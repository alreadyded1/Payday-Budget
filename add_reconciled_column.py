#!/usr/bin/env python3
"""
Migration script to add reconciled column to transaction table
"""
import sqlite3
import os

# Database paths to check
db_paths = [
    'instance/payday_budget.db',
    'payday_budget.db'
]

def migrate_database(db_path):
    """Add reconciled column to transaction table if it doesn't exist"""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info([transaction])")
        columns = [column[1] for column in cursor.fetchall()]

        if 'reconciled' in columns:
            print(f"  Column 'reconciled' already exists in {db_path}")
            return True

        # Add the reconciled column
        cursor.execute("""
            ALTER TABLE [transaction]
            ADD COLUMN reconciled BOOLEAN NOT NULL DEFAULT 0
        """)

        conn.commit()
        print(f"  Successfully added 'reconciled' column to {db_path}")
        return True

    except sqlite3.Error as e:
        print(f"  Error migrating {db_path}: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    print("Transaction Reconciliation Migration")
    print("=" * 50)

    migrated = False
    for db_path in db_paths:
        if migrate_database(db_path):
            migrated = True

    if migrated:
        print("\nMigration completed successfully!")
    else:
        print("\nNo databases were migrated.")
