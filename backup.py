import os
import shutil
import argparse
import datetime

def backup_db():
    db_file = "db.sqlite3"
    if not os.path.exists(db_file):
        print(f"Error: {db_file} not found.")
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f"db_backup_{timestamp}.sqlite3")
    shutil.copy2(db_file, backup_file)
    print(f"Database backed up successfully to: {backup_file}")

def backup_media():
    media_dir = "media"
    if not os.path.exists(media_dir):
        print(f"Error: {media_dir} directory not found.")
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_file = os.path.join(backup_dir, f"media_backup_{timestamp}")
    shutil.make_archive(backup_file, 'zip', media_dir)
    print(f"Media files backed up successfully to: {backup_file}.zip")

def main():
    parser = argparse.ArgumentParser(description="Backup script for database and uploaded media files.")
    parser.add_argument('--db', action='store_true', help="Backup the SQLite database")
    parser.add_argument('--media', action='store_true', help="Backup the media/uploaded files directory")
    parser.add_argument('--all', action='store_true', help="Backup both database and media files")
    
    args = parser.parse_args()
    
    if not any([args.db, args.media, args.all]):
        parser.print_help()
        print("\nPlease specify what to backup using --db, --media, or --all")
        return
    
    if args.all or args.db:
        backup_db()
        
    if args.all or args.media:
        backup_media()

if __name__ == "__main__":
    main()
