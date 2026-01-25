#!/usr/bin/env python3
"""
Database migration script for Budget Recurrence System
This script migrates from Pay Periods to Budget Recurrence
"""

import os
import shutil
from datetime import datetime, date
from app import app, db
from models import User, Account, Payee, Category, Transaction, Budget

def backup_database():
    """Create a backup of the current database"""
    # Check both possible locations
    db_paths = ['instance/payday_budget.db', 'payday_budget.db']

    for db_path in db_paths:
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.dirname(db_path) or '.'
            backup_path = os.path.join(backup_dir, f'payday_budget_backup_recurrence_{timestamp}.db')
            shutil.copy2(db_path, backup_path)
            print(f"✓ Database backed up to {backup_path}")
            return True

    print("ℹ No existing database found, creating new one")
    return False

def migrate_schema():
    """Migrate from Pay Periods to Budget Recurrence"""
    with app.app_context():
        print("\nMigrating to Budget Recurrence System...")

        # Backup first
        backup_database()

        print("✓ Dropping PayPeriod table and recreating Budget table...")

        # We need to recreate tables due to SQLite limitations
        db.drop_all()
        db.create_all()

        print("✓ Database schema updated successfully!")
        print("\nChanges:")
        print("- Removed Pay Periods feature")
        print("- Budgets now have recurrence types: Weekly, Bi-Weekly, Monthly")
        print("- Budgets automatically reset based on recurrence interval")
        print("\nNOTE: All existing data has been cleared due to schema changes.")
        print("If you had important data, it's in the backup file created above.")
        print("\nNext steps:")
        print("1. Register or login to your account")
        print("2. Set up your categories")
        print("3. Create budgets with recurrence intervals")
        print("4. Start tracking your transactions!")

if __name__ == '__main__':
    try:
        migrate_schema()
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        print("Your database backup is safe. Please check the error and try again.")
        exit(1)
