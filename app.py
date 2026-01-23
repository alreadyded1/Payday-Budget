from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, PayPeriod, Category, Transaction, Budget
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
        total_spent = db.session.query(func.sum(Transaction.amount))\
            .filter_by(user_id=current_user.id, pay_period_id=current_period.id)\
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

@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    if request.method == 'POST':
        pay_period_id = request.form.get('pay_period_id')
        category_id = request.form.get('category_id')
        description = request.form.get('description')
        amount = float(request.form.get('amount'))
        transaction_date = datetime.strptime(request.form.get('transaction_date'), '%Y-%m-%d').date()

        transaction = Transaction(
            user_id=current_user.id,
            pay_period_id=int(pay_period_id),
            category_id=int(category_id),
            description=description,
            amount=amount,
            transaction_date=transaction_date
        )
        db.session.add(transaction)
        db.session.commit()

        flash('Transaction added successfully!', 'success')
        return redirect(url_for('transactions'))

    all_transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.transaction_date.desc())\
        .all()

    pay_periods = PayPeriod.query.filter_by(user_id=current_user.id)\
        .order_by(PayPeriod.start_date.desc())\
        .all()

    all_categories = Category.query.filter_by(user_id=current_user.id).all()

    return render_template('transactions.html',
                         transactions=all_transactions,
                         pay_periods=pay_periods,
                         categories=all_categories)

@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted successfully!', 'success')
    return redirect(url_for('transactions'))

@app.route('/budgets', methods=['GET', 'POST'])
@login_required
def budgets():
    if request.method == 'POST':
        category_id = request.form.get('category_id')
        pay_period_id = request.form.get('pay_period_id')
        planned_amount = float(request.form.get('planned_amount'))

        budget = Budget(
            user_id=current_user.id,
            category_id=int(category_id),
            pay_period_id=int(pay_period_id) if pay_period_id else None,
            planned_amount=planned_amount
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
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id
    )

    if period_filter:
        spending_by_category = spending_by_category.filter(Transaction.pay_period_id == int(period_filter))

    spending_by_category = spending_by_category.group_by(Category.id).all()

    monthly_spending = db.session.query(
        extract('year', Transaction.transaction_date).label('year'),
        extract('month', Transaction.transaction_date).label('month'),
        func.sum(Transaction.amount).label('total')
    ).filter(
        Transaction.user_id == current_user.id
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
    ).join(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.pay_period_id == period_id
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
