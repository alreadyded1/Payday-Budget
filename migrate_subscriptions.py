#!/usr/bin/env python3
"""
Migration script to add the subscriptions table to existing databases.
Run this after pulling the latest code with subscriptions feature.
"""

from app import app, db
from models import Subscription

def migrate():
    with app.app_context():
        print("Creating subscriptions table...")
        db.create_all()
        print("✓ Subscriptions table created successfully!")
        print("\nYou can now use the subscription tracker feature.")

if __name__ == '__main__':
    migrate()
