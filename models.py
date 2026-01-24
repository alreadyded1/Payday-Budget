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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class PayPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    period_type = db.Column(db.String(20), nullable=False)  # Weekly, Bi-Weekly, Monthly
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    income = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='pay_period', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def calculate_end_date(start_date, period_type):
        if period_type == 'Weekly':
            return start_date + timedelta(days=6)
        elif period_type == 'Bi-Weekly':
            return start_date + timedelta(days=13)
        elif period_type == 'Monthly':
            return (start_date + relativedelta(months=1)) - timedelta(days=1)
        return start_date

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    color = db.Column(db.String(7), default='#3498db')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy=True)
    transactions = db.relationship('Transaction', backref='category', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pay_period_id = db.Column(db.Integer, db.ForeignKey('pay_period.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    pay_period_id = db.Column(db.Integer, db.ForeignKey('pay_period.id'), nullable=True)
    planned_amount = db.Column(db.Float, nullable=False)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category_rel = db.relationship('Category', backref='budgets')
