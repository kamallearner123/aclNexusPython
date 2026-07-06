"""
SQLite Database Migration Script
Version: 1.0.0
Author: Apt Computing Labs
Description: Safely migrates data across SQLite database schemas by matching available columns.
"""
import sqlite3
import os

def migrate_data(old_db_path, new_db_path):
    if not os.path.exists(old_db_path):
        print(f"Error: Old database '{old_db_path}' not found.")
        return
        
    if not os.path.exists(new_db_path):
        print(f"Error: New database '{new_db_path}' not found. Please run 'python manage.py migrate' first to create the schema.")
        return

    old_conn = sqlite3.connect(old_db_path)
    new_conn = sqlite3.connect(new_db_path)
    
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()
    
    # Get all tables from old db
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in old_cursor.fetchall() if not row[0].startswith('sqlite_')]
    
    # Turn off foreign key constraints during migration to avoid insertion order issues
    new_cursor.execute("PRAGMA foreign_keys = OFF;")
    
    try:
        for table in tables:
            print(f"Migrating table: {table}...")
            
            # Check if table exists in new db
            new_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
            if not new_cursor.fetchone():
                print(f"  -> Skipping '{table}' (does not exist in new database schema).")
                continue
                
            # Get columns for old table
            old_cursor.execute(f"PRAGMA table_info({table})")
            old_columns = [col[1] for col in old_cursor.fetchall()]
            
            # Get columns for new table
            new_cursor.execute(f"PRAGMA table_info({table})")
            new_columns = [col[1] for col in new_cursor.fetchall()]
            
            # Find common columns that exist in BOTH databases
            common_columns = [col for col in old_columns if col in new_columns]
            
            if not common_columns:
                print(f"  -> Skipping '{table}' (no matching columns found).")
                continue
                
            col_names = ", ".join(common_columns)
            placeholders = ", ".join(["?"] * len(common_columns))
            
            # Fetch data from old db for the matching columns
            old_cursor.execute(f"SELECT {col_names} FROM {table}")
            rows = old_cursor.fetchall()
            
            if not rows:
                print(f"  -> No data in '{table}'.")
                continue
                
            # Clear existing data in the new table before migrating to prevent UNIQUE constraint errors
            new_cursor.execute(f"DELETE FROM {table}")
            
            # Insert the carefully matched data into the new db
            insert_query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
            new_cursor.executemany(insert_query, rows)
            
            print(f"  -> Successfully migrated {len(rows)} records for '{table}'.")
            
        new_conn.commit()
        print("\nMigration completed successfully!")
    
    except Exception as e:
        new_conn.rollback()
        print(f"\nError during migration: {e}")
        
    finally:
        # Re-enable foreign key constraints
        new_cursor.execute("PRAGMA foreign_keys = ON;")
        old_conn.close()
        new_conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Safely migrate data from an old SQLite database to a new one, adapting to model changes.")
    parser.add_argument("--old", default="old_db.sqlite3", help="Path to the old SQLite database (e.g. old_db.sqlite3).")
    parser.add_argument("--new", default="db.sqlite3", help="Path to the new SQLite database (e.g. db.sqlite3).")
    
    args = parser.parse_args()
    
    print(f"Preparing to migrate data from '{args.old}' to '{args.new}'...")
    migrate_data(args.old, args.new)
