from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User, Category, Transaction, Budget, Account, Payee, Settings
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract, case
from dotenv import load_dotenv
import os
import secrets

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Security Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///payday_budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session Security
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('HTTPS_ENABLED', 'False').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# CSRF Protection
csrf = CSRFProtect(app)

# Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Security Headers Middleware
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; img-src 'self' data:;"
    return response

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Input validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('login.html')

        if len(username) > 80:
            flash('Invalid username or password', 'danger')
            return render_template('login.html')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    # Check if registration is enabled
    registration_enabled = Settings.get_value('registration_enabled', 'true')
    if registration_enabled.lower() != 'true':
        flash('Registration is currently disabled. Please contact an administrator.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Input validation
        if not username or not password:
            flash('Username and password are required', 'danger')
            return render_template('register.html')

        if len(username) < 3 or len(username) > 80:
            flash('Username must be between 3 and 80 characters', 'danger')
            return render_template('register.html')

        if len(password) < 4:
            flash('Password must be at least 4 characters long', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')

        # Check for alphanumeric username (basic sanitization)
        if not username.replace('_', '').replace('-', '').isalnum():
            flash('Username can only contain letters, numbers, underscores, and hyphens', 'danger')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return render_template('register.html')

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create default categories
        default_categories = [
            {'name': 'Housing', 'color': '#e74c3c'},
            {'name': 'Transportation', 'color': '#3498db'},
            {'name': 'Food', 'color': '#2ecc71'},
            {'name': 'Utilities', 'color': '#f39c12'},
            {'name': 'Entertainment', 'color': '#9b59b6'},
            {'name': 'Healthcare', 'color': '#1abc9c'},
            {'name': 'Savings', 'color': '#27ae60'},
            {'name': 'Other', 'color': '#95a5a6'}
        ]

        for cat_data in default_categories:
            category = Category(user_id=user.id, name=cat_data['name'], color=cat_data['color'])
            db.session.add(category)

        # Create default account
        default_account = Account(
            user_id=user.id,
            name='Main Checking',
            account_type='Checking',
            balance=0.0,
            opening_balance=0.0,
            include_in_budget=True
        )
        db.session.add(default_account)

        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get current month's date range
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)

    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.transaction_date.desc())\
        .limit(10)\
        .all()

    categories = Category.query.filter_by(user_id=current_user.id, parent_id=None).all()

    # Calculate total spent this month from budget-included accounts (debits - credits)
    total_debits = db.session.query(func.sum(Transaction.amount))\
        .join(Account)\
        .filter(Transaction.user_id == current_user.id)\
        .filter(Transaction.transaction_date >= month_start)\
        .filter(Transaction.transaction_date <= month_end)\
        .filter(Transaction.transaction_type == 'Debit')\
        .filter(Account.include_in_budget == True)\
        .scalar() or 0

    total_credits = db.session.query(func.sum(Transaction.amount))\
        .join(Account)\
        .filter(Transaction.user_id == current_user.id)\
        .filter(Transaction.transaction_date >= month_start)\
        .filter(Transaction.transaction_date <= month_end)\
        .filter(Transaction.transaction_type == 'Credit')\
        .filter(Account.include_in_budget == True)\
        .scalar() or 0

    total_spent = total_debits - total_credits

    # Get all active budgets and calculate totals
    all_budgets = Budget.query.filter_by(user_id=current_user.id).all()

    # Auto-reset budgets that need it
    for budget in all_budgets:
        if budget.needs_reset():
            budget.reset_period()
    db.session.commit()

    total_budget = sum(budget.planned_amount for budget in all_budgets)

    # Calculate budget progress by category
    budget_progress = []
    for budget in all_budgets:
        debits = db.session.query(func.sum(Transaction.amount))\
            .join(Account)\
            .filter(Transaction.user_id == current_user.id)\
            .filter(Transaction.category_id == budget.category_id)\
            .filter(Transaction.transaction_date >= budget.period_start_date)\
            .filter(Transaction.transaction_date <= budget.get_period_end_date())\
            .filter(Transaction.transaction_type == 'Debit')\
            .filter(Account.include_in_budget == True)\
            .scalar() or 0

        credits = db.session.query(func.sum(Transaction.amount))\
            .join(Account)\
            .filter(Transaction.user_id == current_user.id)\
            .filter(Transaction.category_id == budget.category_id)\
            .filter(Transaction.transaction_date >= budget.period_start_date)\
            .filter(Transaction.transaction_date <= budget.get_period_end_date())\
            .filter(Transaction.transaction_type == 'Credit')\
            .filter(Account.include_in_budget == True)\
            .scalar() or 0

        spent = debits - credits

        budget_progress.append({
            'budget': budget,
            'spent': spent,
            'remaining': budget.planned_amount - spent,
            'percentage': (spent / budget.planned_amount * 100) if budget.planned_amount > 0 else 0
        })

    return render_template('dashboard.html',
                         month_start=month_start,
                         month_end=month_end,
                         recent_transactions=recent_transactions,
                         categories=categories,
                         total_spent=total_spent,
                         total_budget=total_budget,
                         budget_progress=budget_progress)

@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    if request.method == 'POST':
        name = request.form.get('name')
        parent_id = request.form.get('parent_id')
        color = request.form.get('color', '#3498db')

        category = Category(
            user_id=current_user.id,
            name=name,
            parent_id=int(parent_id) if parent_id else None,
            color=color
        )
        db.session.add(category)
        db.session.commit()

        flash('Category created successfully!', 'success')
        return redirect(url_for('categories'))

    # Get time period filter
    period = request.args.get('period', 'mtd')  # Default to Month to Date

    # Calculate date range based on period
    today = date.today()
    if period == 'mtd':
        start_date = date(today.year, today.month, 1)
        end_date = today
        period_label = 'Month to Date'
    elif period == 'ytd':
        start_date = date(today.year, 1, 1)
        end_date = today
        period_label = 'Year to Date'
    else:  # all time
        start_date = None
        end_date = None
        period_label = 'All Time'

    # Get parent categories sorted alphabetically, then their subcategories
    parent_categories_sorted = Category.query.filter_by(user_id=current_user.id, parent_id=None).order_by(Category.name).all()

    # Build list with parents followed by their subcategories (both sorted alphabetically)
    all_categories = []
    for parent in parent_categories_sorted:
        all_categories.append(parent)
        # Add subcategories for this parent, sorted alphabetically
        subcategories = Category.query.filter_by(user_id=current_user.id, parent_id=parent.id).order_by(Category.name).all()
        all_categories.extend(subcategories)

    # Calculate totals for each category
    categories_with_totals = []
    for category in all_categories:
        # Calculate debits
        debit_query = db.session.query(func.sum(Transaction.amount))\
            .join(Account)\
            .filter(Transaction.user_id == current_user.id)\
            .filter(Transaction.category_id == category.id)\
            .filter(Transaction.transaction_type == 'Debit')\
            .filter(Account.include_in_budget == True)

        if start_date and end_date:
            debit_query = debit_query.filter(Transaction.transaction_date >= start_date)\
                         .filter(Transaction.transaction_date <= end_date)

        total_debits = debit_query.scalar() or 0.0

        # Calculate credits
        credit_query = db.session.query(func.sum(Transaction.amount))\
            .join(Account)\
            .filter(Transaction.user_id == current_user.id)\
            .filter(Transaction.category_id == category.id)\
            .filter(Transaction.transaction_type == 'Credit')\
            .filter(Account.include_in_budget == True)

        if start_date and end_date:
            credit_query = credit_query.filter(Transaction.transaction_date >= start_date)\
                         .filter(Transaction.transaction_date <= end_date)

        total_credits = credit_query.scalar() or 0.0

        # Net total: debits - credits
        total = total_debits - total_credits

        categories_with_totals.append({
            'category': category,
            'total': total
        })

    # Get parent categories for the form dropdown
    parent_categories = Category.query.filter_by(user_id=current_user.id, parent_id=None)\
                                      .order_by(Category.name).all()

    return render_template('categories.html',
                         categories=categories_with_totals,
                         parent_categories=parent_categories,
                         current_period=period,
                         period_label=period_label)

@app.route('/categories/<int:category_id>/edit', methods=['POST'])
@login_required
def edit_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()

    name = request.form.get('name')
    parent_id = request.form.get('parent_id')

    if name:
        category.name = name
        category.parent_id = int(parent_id) if parent_id else None
        db.session.commit()
        flash('Category updated successfully!', 'success')

    return redirect(url_for('categories'))

@app.route('/categories/<int:category_id>/transactions')
@login_required
def category_transactions(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()

    # Get time period filter
    period = request.args.get('period', 'mtd')

    # Calculate date range
    today = date.today()
    if period == 'mtd':
        start_date = date(today.year, today.month, 1)
        end_date = today
        period_label = 'Month to Date'
    elif period == 'ytd':
        start_date = date(today.year, 1, 1)
        end_date = today
        period_label = 'Year to Date'
    else:
        start_date = None
        end_date = None
        period_label = 'All Time'

    # Get transactions for this category
    query = Transaction.query.join(Account)\
        .filter(Transaction.user_id == current_user.id)\
        .filter(Transaction.category_id == category_id)\
        .filter(Account.include_in_budget == True)

    if start_date and end_date:
        query = query.filter(Transaction.transaction_date >= start_date)\
                     .filter(Transaction.transaction_date <= end_date)

    transactions = query.order_by(Transaction.transaction_date.desc()).all()

    # Calculate total (debits - credits)
    total_debits = sum(t.amount for t in transactions if t.transaction_type == 'Debit')
    total_credits = sum(t.amount for t in transactions if t.transaction_type == 'Credit')
    total = total_debits - total_credits

    return render_template('category_transactions.html',
                         category=category,
                         transactions=transactions,
                         total=total,
                         current_period=period,
                         period_label=period_label)

@app.route('/categories/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('categories'))

@app.route('/accounts', methods=['GET', 'POST'])
@login_required
def accounts():
    if request.method == 'POST':
        name = request.form.get('name')
        account_type = request.form.get('account_type')
        opening_balance = float(request.form.get('opening_balance', 0))
        include_in_budget = request.form.get('include_in_budget') == 'on'

        account = Account(
            user_id=current_user.id,
            name=name,
            account_type=account_type,
            balance=opening_balance,
            opening_balance=opening_balance,
            include_in_budget=include_in_budget
        )
        db.session.add(account)
        db.session.commit()

        flash('Account created successfully!', 'success')
        return redirect(url_for('accounts'))

    all_accounts = Account.query.filter_by(user_id=current_user.id).all()

    # Calculate total balances by type
    total_checking = sum(a.balance for a in all_accounts if a.account_type == 'Checking' and a.is_active)
    total_savings = sum(a.balance for a in all_accounts if a.account_type == 'Savings' and a.is_active)
    total_cash = sum(a.balance for a in all_accounts if a.account_type == 'Cash' and a.is_active)

    return render_template('accounts.html',
                         accounts=all_accounts,
                         total_checking=total_checking,
                         total_savings=total_savings,
                         total_cash=total_cash)

@app.route('/accounts/<int:account_id>/toggle-budget', methods=['POST'])
@login_required
def toggle_account_budget(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    account.include_in_budget = not account.include_in_budget
    db.session.commit()
    flash(f'Account budget setting updated!', 'success')
    return redirect(url_for('accounts'))

@app.route('/accounts/<int:account_id>/toggle-active', methods=['POST'])
@login_required
def toggle_account_active(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    account.is_active = not account.is_active
    db.session.commit()
    flash(f'Account status updated!', 'success')
    return redirect(url_for('accounts'))

@app.route('/accounts/<int:account_id>/delete', methods=['POST'])
@login_required
def delete_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    # Check if account has transactions
    transaction_count = Transaction.query.filter_by(account_id=account_id).count()
    if transaction_count > 0:
        flash(f'Cannot delete account with {transaction_count} transactions. Please delete transactions first.', 'danger')
        return redirect(url_for('accounts'))

    db.session.delete(account)
    db.session.commit()
    flash('Account deleted successfully!', 'success')
    return redirect(url_for('accounts'))

@app.route('/account/<int:account_id>', methods=['GET', 'POST'])
@login_required
def account_transactions(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        payee_id = request.form.get('payee_id')
        new_payee_name = request.form.get('new_payee_name')
        category_id = request.form.get('category_id')
        transaction_type = request.form.get('transaction_type')
        description = request.form.get('description', '')
        amount = float(request.form.get('amount'))
        transaction_date = datetime.strptime(request.form.get('transaction_date'), '%Y-%m-%d').date()

        # Create new payee if name provided
        if new_payee_name and not payee_id:
            new_payee = Payee(
                user_id=current_user.id,
                name=new_payee_name,
                default_category_id=int(category_id) if category_id else None
            )
            db.session.add(new_payee)
            db.session.flush()
            payee_id = new_payee.id

        # Validate payee_id and category_id
        if not payee_id:
            flash('Please select a payee or enter a new payee name.', 'error')
            return redirect(url_for('account_transactions', account_id=account_id))

        if not category_id:
            flash('Please select a category.', 'error')
            return redirect(url_for('account_transactions', account_id=account_id))

        transaction = Transaction(
            user_id=current_user.id,
            account_id=account_id,
            payee_id=int(payee_id),
            category_id=int(category_id),
            transaction_type=transaction_type,
            description=description,
            amount=amount,
            transaction_date=transaction_date
        )
        db.session.add(transaction)

        # Update account balance
        if transaction_type == 'Debit':
            account.balance -= amount
        else:  # Credit
            account.balance += amount

        db.session.commit()

        flash('Transaction added successfully!', 'success')
        return redirect(url_for('account_transactions', account_id=account_id))

    # Get all transactions for this account
    transactions = Transaction.query.filter_by(account_id=account_id)\
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())\
        .all()

    # Calculate running balance for each transaction
    running_balance = account.opening_balance
    transactions_with_balance = []

    # We need to process in chronological order to calculate balance
    for transaction in reversed(transactions):
        if transaction.transaction_type == 'Credit':
            running_balance += transaction.amount
        else:  # Debit
            running_balance -= transaction.amount

        # Add running balance to transaction object
        transaction.running_balance = running_balance
        transactions_with_balance.insert(0, transaction)

    payees = Payee.query.filter_by(user_id=current_user.id).order_by(Payee.name).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()

    # Calculate reconciled amount
    reconciled_debits = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.account_id == account_id)\
        .filter(Transaction.reconciled == True)\
        .filter(Transaction.transaction_type == 'Debit')\
        .scalar() or 0.0

    reconciled_credits = db.session.query(func.sum(Transaction.amount))\
        .filter(Transaction.account_id == account_id)\
        .filter(Transaction.reconciled == True)\
        .filter(Transaction.transaction_type == 'Credit')\
        .scalar() or 0.0

    reconciled_balance = account.opening_balance + reconciled_credits - reconciled_debits

    return render_template('account_transactions.html',
                         account=account,
                         transactions=transactions_with_balance,
                         payees=payees,
                         categories=categories,
                         reconciled_balance=reconciled_balance,
                         today=date.today().isoformat())

@app.route('/payees', methods=['GET', 'POST'])
@login_required
def payees():
    if request.method == 'POST':
        name = request.form.get('name')
        default_category_id = request.form.get('default_category_id')

        payee = Payee(
            user_id=current_user.id,
            name=name,
            default_category_id=int(default_category_id) if default_category_id else None
        )
        db.session.add(payee)
        db.session.commit()

        flash('Payee created successfully!', 'success')
        return redirect(url_for('payees'))

    all_payees = Payee.query.filter_by(user_id=current_user.id).order_by(Payee.name).all()
    all_categories = Category.query.filter_by(user_id=current_user.id).all()

    return render_template('payees.html', payees=all_payees, categories=all_categories)

@app.route('/payees/<int:payee_id>/edit', methods=['POST'])
@login_required
def edit_payee(payee_id):
    payee = Payee.query.filter_by(id=payee_id, user_id=current_user.id).first_or_404()

    name = request.form.get('name')
    default_category_id = request.form.get('default_category_id')

    if name:
        payee.name = name
        payee.default_category_id = int(default_category_id) if default_category_id else None
        db.session.commit()
        flash('Payee updated successfully!', 'success')

    return redirect(url_for('payees'))

@app.route('/payees/<int:payee_id>/delete', methods=['POST'])
@login_required
def delete_payee(payee_id):
    payee = Payee.query.filter_by(id=payee_id, user_id=current_user.id).first_or_404()

    # Check if payee has transactions
    transaction_count = Transaction.query.filter_by(payee_id=payee_id).count()
    if transaction_count > 0:
        flash(f'Cannot delete payee with {transaction_count} transactions. Please delete transactions first.', 'danger')
        return redirect(url_for('payees'))

    db.session.delete(payee)
    db.session.commit()
    flash('Payee deleted successfully!', 'success')
    return redirect(url_for('payees'))

@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    # Redirect to accounts page - transactions are now managed per account
    return redirect(url_for('accounts'))

@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
    account_id = transaction.account_id

    # Reverse account balance change
    account = db.session.get(Account, transaction.account_id)
    if transaction.transaction_type == 'Debit':
        account.balance += transaction.amount
    else:  # Credit
        account.balance -= transaction.amount

    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('account_transactions', account_id=account_id))

@app.route('/transactions/<int:transaction_id>/edit', methods=['POST'])
@login_required
def edit_transaction(transaction_id):
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
    account_id = transaction.account_id
    account = db.session.get(Account, account_id)

    # Get old values to reverse balance
    old_type = transaction.transaction_type
    old_amount = transaction.amount

    # Get new values from form
    payee_id = request.form.get('payee_id')
    category_id = request.form.get('category_id')
    transaction_type = request.form.get('transaction_type')
    description = request.form.get('description', '')
    amount = float(request.form.get('amount'))
    transaction_date = datetime.strptime(request.form.get('transaction_date'), '%Y-%m-%d').date()

    # Validate inputs
    if not payee_id or not category_id:
        flash('Please select a payee and category.', 'error')
        return redirect(url_for('account_transactions', account_id=account_id))

    # Reverse old transaction impact on balance
    if old_type == 'Debit':
        account.balance += old_amount
    else:  # Credit
        account.balance -= old_amount

    # Update transaction fields
    transaction.payee_id = int(payee_id)
    transaction.category_id = int(category_id)
    transaction.transaction_type = transaction_type
    transaction.description = description
    transaction.amount = amount
    transaction.transaction_date = transaction_date

    # Apply new transaction impact on balance
    if transaction_type == 'Debit':
        account.balance -= amount
    else:  # Credit
        account.balance += amount

    db.session.commit()

    flash('Transaction updated successfully!', 'success')
    return redirect(url_for('account_transactions', account_id=account_id))

@app.route('/transactions/<int:transaction_id>/toggle_reconciled', methods=['POST'])
@login_required
@csrf.exempt  # CSRF handled by JavaScript fetch
def toggle_reconciled(transaction_id):
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
    transaction.reconciled = not transaction.reconciled
    db.session.commit()
    return jsonify({'success': True, 'reconciled': transaction.reconciled})

@app.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        planned_amount = float(request.form.get('planned_amount'))
        recurrence_type = request.form.get('recurrence_type', 'Monthly')
        start_date_str = request.form.get('period_start_date')

        # Use provided start date or default to today
        if start_date_str:
            period_start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            period_start_date = date.today()

        budget = Budget(
            user_id=current_user.id,
            category_id=int(category_id),
            planned_amount=planned_amount,
            recurrence_type=recurrence_type,
            period_start_date=period_start_date
        )
        db.session.add(budget)
        db.session.commit()

        flash('Budget created successfully!', 'success')
        return redirect(url_for('budgets'))

    # Get all budgets and auto-reset any that need it
    all_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    for budget in all_budgets:
        if budget.needs_reset():
            budget.reset_period()
    db.session.commit()

    # Calculate spending for each budget (debits - credits)
    budgets_with_progress = []
    for budget in all_budgets:
        debits = db.session.query(func.sum(Transaction.amount))\
            .join(Account)\
            .filter(Transaction.user_id == current_user.id)\
            .filter(Transaction.category_id == budget.category_id)\
            .filter(Transaction.transaction_date >= budget.period_start_date)\
            .filter(Transaction.transaction_date <= budget.get_period_end_date())\
            .filter(Transaction.transaction_type == 'Debit')\
            .filter(Account.include_in_budget == True)\
            .scalar() or 0

        credits = db.session.query(func.sum(Transaction.amount))\
            .join(Account)\
            .filter(Transaction.user_id == current_user.id)\
            .filter(Transaction.category_id == budget.category_id)\
            .filter(Transaction.transaction_date >= budget.period_start_date)\
            .filter(Transaction.transaction_date <= budget.get_period_end_date())\
            .filter(Transaction.transaction_type == 'Credit')\
            .filter(Account.include_in_budget == True)\
            .scalar() or 0

        spent = debits - credits

        budgets_with_progress.append({
            'budget': budget,
            'spent': spent,
            'remaining': budget.planned_amount - spent,
            'percentage': (spent / budget.planned_amount * 100) if budget.planned_amount > 0 else 0
        })

    all_categories = Category.query.filter_by(user_id=current_user.id).all()

    return render_template('budgets.html',
                         budgets=budgets_with_progress,
                         categories=all_categories,
                         today=date.today().isoformat())

@app.route('/budgets/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted successfully!', 'success')
    return redirect(url_for('budgets'))

@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    if request.method == 'POST':
        from_account_id = request.form.get('from_account_id')
        to_account_id = request.form.get('to_account_id')
        amount = float(request.form.get('amount'))
        transfer_date = datetime.strptime(request.form.get('transfer_date'), '%Y-%m-%d').date()
        description = request.form.get('description', '')

        # Validation
        if not from_account_id or not to_account_id:
            flash('Please select both source and destination accounts.', 'error')
            return redirect(url_for('transfer'))

        if from_account_id == to_account_id:
            flash('Cannot transfer to the same account.', 'error')
            return redirect(url_for('transfer'))

        if amount <= 0:
            flash('Transfer amount must be greater than zero.', 'error')
            return redirect(url_for('transfer'))

        # Get accounts
        from_account = Account.query.filter_by(id=from_account_id, user_id=current_user.id).first_or_404()
        to_account = Account.query.filter_by(id=to_account_id, user_id=current_user.id).first_or_404()

        # Get or create "Transfer" payee and category
        transfer_payee = Payee.query.filter_by(user_id=current_user.id, name='Transfer').first()
        if not transfer_payee:
            transfer_payee = Payee(user_id=current_user.id, name='Transfer')
            db.session.add(transfer_payee)
            db.session.flush()

        transfer_category = Category.query.filter_by(user_id=current_user.id, name='Transfer').first()
        if not transfer_category:
            transfer_category = Category(user_id=current_user.id, name='Transfer', color='#6c757d')
            db.session.add(transfer_category)
            db.session.flush()

        # Create debit transaction for source account
        debit_transaction = Transaction(
            user_id=current_user.id,
            account_id=from_account.id,
            payee_id=transfer_payee.id,
            category_id=transfer_category.id,
            transaction_type='Debit',
            description=f"Transfer to {to_account.name}" + (f" - {description}" if description else ""),
            amount=amount,
            transaction_date=transfer_date
        )
        db.session.add(debit_transaction)

        # Create credit transaction for destination account
        credit_transaction = Transaction(
            user_id=current_user.id,
            account_id=to_account.id,
            payee_id=transfer_payee.id,
            category_id=transfer_category.id,
            transaction_type='Credit',
            description=f"Transfer from {from_account.name}" + (f" - {description}" if description else ""),
            amount=amount,
            transaction_date=transfer_date
        )
        db.session.add(credit_transaction)

        # Update account balances
        from_account.balance -= amount
        to_account.balance += amount

        db.session.commit()

        flash(f'Transfer of ${amount:.2f} from {from_account.name} to {to_account.name} completed successfully!', 'success')
        return redirect(url_for('transfer'))

    # GET request - show transfer form
    accounts = Account.query.filter_by(user_id=current_user.id, is_active=True).order_by(Account.name).all()

    return render_template('transfer.html',
                         accounts=accounts,
                         today=date.today().isoformat())

@app.route('/reports')
@login_required
def reports():
    # Get period filter (mtd, ytd, all)
    period = request.args.get('period', 'mtd')

    # Calculate date range based on period
    today = date.today()
    if period == 'mtd':
        start_date = date(today.year, today.month, 1)
        end_date = today
        period_label = 'Month to Date'
    elif period == 'ytd':
        start_date = date(today.year, 1, 1)
        end_date = today
        period_label = 'Year to Date'
    else:  # all time
        start_date = None
        end_date = None
        period_label = 'All Time'

    # Build spending by category query (debits - credits)
    spending_by_category = db.session.query(
        Category.name,
        Category.color,
        func.sum(case(
            (Transaction.transaction_type == 'Debit', Transaction.amount),
            (Transaction.transaction_type == 'Credit', -Transaction.amount),
            else_=0
        )).label('total')
    ).join(Transaction).join(Account).filter(
        Transaction.user_id == current_user.id,
        Account.include_in_budget == True
    )

    if start_date and end_date:
        spending_by_category = spending_by_category.filter(
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date
        )

    spending_by_category = spending_by_category.group_by(Category.id).all()

    # Monthly spending trend (last 12 months, debits - credits)
    monthly_spending = db.session.query(
        extract('year', Transaction.transaction_date).label('year'),
        extract('month', Transaction.transaction_date).label('month'),
        func.sum(case(
            (Transaction.transaction_type == 'Debit', Transaction.amount),
            (Transaction.transaction_type == 'Credit', -Transaction.amount),
            else_=0
        )).label('total')
    ).join(Account).filter(
        Transaction.user_id == current_user.id,
        Account.include_in_budget == True
    ).group_by('year', 'month').order_by('year', 'month').limit(12).all()

    return render_template('reports.html',
                         spending_by_category=spending_by_category,
                         monthly_spending=monthly_spending,
                         current_period=period,
                         period_label=period_label)

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    # Check if user is admin
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'toggle_registration':
            current_value = Settings.get_value('registration_enabled', 'true')
            new_value = 'false' if current_value.lower() == 'true' else 'true'
            Settings.set_value('registration_enabled', new_value)
            status = 'enabled' if new_value == 'true' else 'disabled'
            flash(f'Registration has been {status}.', 'success')

        elif action == 'make_admin':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            if user:
                user.is_admin = True
                db.session.commit()
                flash(f'User {user.username} is now an admin.', 'success')

        elif action == 'remove_admin':
            user_id = request.form.get('user_id')
            user = User.query.get(user_id)
            if user and user.id != current_user.id:
                user.is_admin = False
                db.session.commit()
                flash(f'Admin privileges removed from {user.username}.', 'success')
            elif user and user.id == current_user.id:
                flash('You cannot remove your own admin privileges.', 'warning')

        elif action == 'change_password':
            user_id = request.form.get('user_id')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if new_password != confirm_password:
                flash('Passwords do not match.', 'danger')
            elif len(new_password) < 4:
                flash('Password must be at least 4 characters long.', 'danger')
            else:
                user = User.query.get(user_id)
                if user:
                    user.set_password(new_password)
                    db.session.commit()
                    flash(f'Password changed successfully for {user.username}.', 'success')
                else:
                    flash('User not found.', 'danger')

        return redirect(url_for('admin'))

    # Get all users
    all_users = User.query.order_by(User.created_at).all()

    # Get current registration setting
    registration_enabled = Settings.get_value('registration_enabled', 'true').lower() == 'true'

    return render_template('admin.html',
                         users=all_users,
                         registration_enabled=registration_enabled)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)
