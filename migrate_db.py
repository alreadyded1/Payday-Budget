#!/usr/bin/env python3
"""
Database migration script for Payday Budget
This script handles schema changes, particularly for the Account/Payee implementation
"""

import os
import shutil
from datetime import datetime
from app import app, db
from models import User, Account, Payee, Category, PayPeriod, Budget, Transaction

def backup_database():
    """Create a backup of the current database"""
    db_path = 'payday_budget.db'
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f'payday_budget_backup_{timestamp}.db'
        shutil.copy2(db_path, backup_path)
        print(f"✓ Database backed up to {backup_path}")
        return True
    return False

def migrate_schema():
    """Migrate the database schema"""
    with app.app_context():
        print("\nStarting database migration...")

        # Backup first
        backup_database()

        # Drop all tables and recreate with new schema
        print("✓ Dropping all tables...")
        db.drop_all()

        print("✓ Creating new schema...")
        db.create_all()

        print("✓ Database schema updated successfully!")
        print("\nNOTE: All existing data has been cleared due to schema changes.")
        print("If you had important data, it's in the backup file created above.")
        print("\nNext steps:")
        print("1. Register a new user account")
        print("2. A default checking account will be created automatically")
        print("3. Set up your categories and pay periods")
        print("4. Start tracking your transactions!")

if __name__ == '__main__':
    try:
        migrate_schema()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print("Your database backup is safe. Please check the error and try again.")
        exit(1)
