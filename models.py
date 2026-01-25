from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    accounts = db.relationship('Account', backref='user', lazy='dynamic')
    categories = db.relationship('Category', backref='user', lazy='dynamic')
    payees = db.relationship('Payee', backref='user', lazy='dynamic')
    transactions = db.relationship('Transaction', backref='user', lazy='dynamic')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    color = db.Column(db.String(7), default='#3498db')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy=True)
    transactions = db.relationship('Transaction', backref='category', lazy=True)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # Checking, Savings, Cash
    balance = db.Column(db.Float, default=0.0)
    opening_balance = db.Column(db.Float, default=0.0)
    include_in_budget = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='account', lazy=True)

class Payee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    default_category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='payee', lazy=True)
    default_category = db.relationship('Category', foreign_keys=[default_category_id])

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    payee_id = db.Column(db.Integer, db.ForeignKey('payee.id'), nullable=False)
    pay_period_id = db.Column(db.Integer, db.ForeignKey('pay_period.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # Debit or Credit
    description = db.Column(db.String(255), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    planned_amount = db.Column(db.Float, nullable=False)
    recurrence_type = db.Column(db.String(20), nullable=False, default='Monthly')  # Weekly, Bi-Weekly, Monthly
    period_start_date = db.Column(db.Date, nullable=False)  # When the current period started
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category_rel = db.relationship('Category', backref='budgets')

    def get_period_end_date(self):
        """Calculate when the current budget period ends"""
        if self.recurrence_type == 'Weekly':
            return self.period_start_date + timedelta(days=6)
        elif self.recurrence_type == 'Bi-Weekly':
            return self.period_start_date + timedelta(days=13)
        elif self.recurrence_type == 'Monthly':
            return (self.period_start_date + relativedelta(months=1)) - timedelta(days=1)
        return self.period_start_date

    def is_period_active(self):
        """Check if we're currently in this budget's period"""
        today = datetime.now().date()
        return self.period_start_date <= today <= self.get_period_end_date()

    def needs_reset(self):
        """Check if the budget period has ended and needs to reset"""
        today = datetime.now().date()
        return today > self.get_period_end_date()

    def reset_period(self):
        """Reset the budget period to the next period"""
        if self.recurrence_type == 'Weekly':
            self.period_start_date += timedelta(days=7)
        elif self.recurrence_type == 'Bi-Weekly':
            self.period_start_date += timedelta(days=14)
        elif self.recurrence_type == 'Monthly':
            self.period_start_date += relativedelta(months=1)
