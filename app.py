from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, PayPeriod, Category, Transaction, Budget, Account, Payee
from datetime import datetime, date
from sqlalchemy import func, extract
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///payday_budget.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
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
    current_period = PayPeriod.query.filter_by(user_id=current_user.id)\
        .filter(PayPeriod.start_date <= date.today())\
        .filter(PayPeriod.end_date >= date.today())\
        .first()

    recent_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.transaction_date.desc())\
        .limit(10)\
        .all()

    categories = Category.query.filter_by(user_id=current_user.id, parent_id=None).all()

    total_spent = 0
    total_budget = 0

    if current_period:
        # Only include transactions from accounts with include_in_budget=True
        total_spent = db.session.query(func.sum(Transaction.amount))\
            .join(Account)\
            .filter(Transaction.user_id == current_user.id)\
            .filter(Transaction.pay_period_id == current_period.id)\
            .filter(Transaction.transaction_type == 'Debit')\
            .filter(Account.include_in_budget == True)\
            .scalar() or 0

        total_budget = db.session.query(func.sum(Budget.planned_amount))\
            .filter_by(user_id=current_user.id, pay_period_id=current_period.id)\
            .scalar() or 0

    return render_template('dashboard.html',
                         current_period=current_period,
                         recent_transactions=recent_transactions,
                         categories=categories,
                         total_spent=total_spent,
                         total_budget=total_budget)

@app.route('/pay-periods', methods=['GET', 'POST'])
@login_required
def pay_periods():
    if request.method == 'POST':
        period_type = request.form.get('period_type')
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        income = float(request.form.get('income', 0))

        end_date = PayPeriod.calculate_end_date(start_date, period_type)

        pay_period = PayPeriod(
            user_id=current_user.id,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            income=income
        )
        db.session.add(pay_period)
        db.session.commit()

        # Copy recurring budgets to this new pay period
        recurring_budgets = Budget.query.filter_by(user_id=current_user.id, is_recurring=True).all()
        for recurring_budget in recurring_budgets:
            new_budget = Budget(
                user_id=current_user.id,
                category_id=recurring_budget.category_id,
                pay_period_id=pay_period.id,
                planned_amount=recurring_budget.planned_amount,
                is_recurring=False
            )
            db.session.add(new_budget)

        db.session.commit()

        flash('Pay period created successfully!', 'success')
        return redirect(url_for('pay_periods'))

    periods = PayPeriod.query.filter_by(user_id=current_user.id)\
        .order_by(PayPeriod.start_date.desc())\
        .all()

    return render_template('pay_periods.html', periods=periods)

@app.route('/pay-periods/<int:period_id>/delete', methods=['POST'])
@login_required
def delete_pay_period(period_id):
    period = PayPeriod.query.filter_by(id=period_id, user_id=current_user.id).first_or_404()
    db.session.delete(period)
    db.session.commit()
    flash('Pay period deleted successfully!', 'success')
    return redirect(url_for('pay_periods'))

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

    all_categories = Category.query.filter_by(user_id=current_user.id, parent_id=None).all()
    return render_template('categories.html', categories=all_categories)

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

        # Find or create pay period for this transaction date
        pay_period = PayPeriod.query.filter_by(user_id=current_user.id)\
            .filter(PayPeriod.start_date <= transaction_date)\
            .filter(PayPeriod.end_date >= transaction_date)\
            .first()

        transaction = Transaction(
            user_id=current_user.id,
            account_id=account_id,
            payee_id=int(payee_id),
            pay_period_id=pay_period.id if pay_period else None,
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

    return render_template('account_transactions.html',
                         account=account,
                         transactions=transactions_with_balance,
                         payees=payees,
                         categories=categories,
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
    account = Account.query.get(transaction.account_id)
    if transaction.transaction_type == 'Debit':
        account.balance += transaction.amount
    else:  # Credit
        account.balance -= transaction.amount

    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('account_transactions', account_id=account_id))

@app.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        pay_period_id = request.form.get('pay_period_id')
        planned_amount = float(request.form.get('planned_amount'))
        is_recurring = request.form.get('is_recurring') == 'on'

        budget = Budget(
            user_id=current_user.id,
            category_id=int(category_id),
            pay_period_id=int(pay_period_id) if pay_period_id else None,
            planned_amount=planned_amount,
            is_recurring=is_recurring
        )
        db.session.add(budget)
        db.session.commit()

        flash('Budget created successfully!', 'success')
        return redirect(url_for('budgets'))

    all_budgets = Budget.query.filter_by(user_id=current_user.id).all()
    pay_periods = PayPeriod.query.filter_by(user_id=current_user.id)\
        .order_by(PayPeriod.start_date.desc())\
        .all()
    all_categories = Category.query.filter_by(user_id=current_user.id).all()

    return render_template('budgets.html',
                         budgets=all_budgets,
                         pay_periods=pay_periods,
                         categories=all_categories)

@app.route('/budgets/<int:budget_id>/delete', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted successfully!', 'success')
    return redirect(url_for('budgets'))

@app.route('/reports')
@login_required
def reports():
    period_filter = request.args.get('period', None)

    query = Transaction.query.filter_by(user_id=current_user.id)

    if period_filter:
        query = query.filter_by(pay_period_id=int(period_filter))

    spending_by_category = db.session.query(
        Category.name,
        Category.color,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).join(Account).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'Debit',
        Account.include_in_budget == True
    )

    if period_filter:
        spending_by_category = spending_by_category.filter(Transaction.pay_period_id == int(period_filter))

    spending_by_category = spending_by_category.group_by(Category.id).all()

    monthly_spending = db.session.query(
        extract('year', Transaction.transaction_date).label('year'),
        extract('month', Transaction.transaction_date).label('month'),
        func.sum(Transaction.amount).label('total')
    ).join(Account).filter(
        Transaction.user_id == current_user.id,
        Transaction.transaction_type == 'Debit',
        Account.include_in_budget == True
    ).group_by('year', 'month').order_by('year', 'month').all()

    pay_periods = PayPeriod.query.filter_by(user_id=current_user.id)\
        .order_by(PayPeriod.start_date.desc())\
        .all()

    return render_template('reports.html',
                         spending_by_category=spending_by_category,
                         monthly_spending=monthly_spending,
                         pay_periods=pay_periods,
                         selected_period=period_filter)

@app.route('/api/category-spending/<int:period_id>')
@login_required
def api_category_spending(period_id):
    spending = db.session.query(
        Category.name,
        Category.color,
        func.sum(Transaction.amount).label('total')
    ).join(Transaction).join(Account).filter(
        Transaction.user_id == current_user.id,
        Transaction.pay_period_id == period_id,
        Transaction.transaction_type == 'Debit',
        Account.include_in_budget == True
    ).group_by(Category.id).all()

    return jsonify([{
        'name': s[0],
        'color': s[1],
        'total': float(s[2])
    } for s in spending])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=False)
