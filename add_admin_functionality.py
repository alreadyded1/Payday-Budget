#!/usr/bin/env python3
"""
Migration script to add admin functionality
- Add is_admin column to user table
- Create settings table
"""
import sqlite3
import os

# Database paths to check
db_paths = [
    'instance/payday_budget.db',
    'payday_budget.db'
]

def migrate_database(db_path):
    """Add admin functionality to database"""
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return False

    print(f"Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if is_admin column exists
        cursor.execute("PRAGMA table_info([user])")
        columns = [column[1] for column in cursor.fetchall()]

        if 'is_admin' not in columns:
            # Add the is_admin column
            cursor.execute("""
                ALTER TABLE [user]
                ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0
            """)
            print(f"  Added 'is_admin' column to user table")
        else:
            print(f"  Column 'is_admin' already exists")

        # Check if settings table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='settings'
        """)

        if not cursor.fetchone():
            # Create settings table
            cursor.execute("""
                CREATE TABLE settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print(f"  Created 'settings' table")

            # Insert default registration_enabled setting
            cursor.execute("""
                INSERT INTO settings (key, value)
                VALUES ('registration_enabled', 'true')
            """)
            print(f"  Added default registration_enabled setting")
        else:
            print(f"  Table 'settings' already exists")

        # Make first user admin if exists
        cursor.execute("SELECT id FROM [user] ORDER BY id ASC LIMIT 1")
        first_user = cursor.fetchone()
        if first_user:
            cursor.execute("UPDATE [user] SET is_admin = 1 WHERE id = ?", (first_user[0],))
            print(f"  Made first user (ID: {first_user[0]}) an admin")

        conn.commit()
        print(f"  Successfully migrated {db_path}")
        return True

    except sqlite3.Error as e:
        print(f"  Error migrating {db_path}: {e}")
        conn.rollback()
        return False

    finally:
        conn.close()

if __name__ == '__main__':
    print("Admin Functionality Migration")
    print("=" * 50)

    migrated = False
    for db_path in db_paths:
        if migrate_database(db_path):
            migrated = True

    if migrated:
        print("\nMigration completed successfully!")
        print("The first user has been made an admin.")
        print("Registration is enabled by default.")
    else:
        print("\nNo databases were migrated.")
