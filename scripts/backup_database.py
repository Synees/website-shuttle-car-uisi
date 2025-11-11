"""
Backup Database
===============

INSTRUKSI:
Script untuk backup database.
Backup akan disimpan dengan timestamp.

CARA PAKAI:
python backup_database.py
"""

import shutil
import os
from datetime import datetime

DATABASE = os.path.join(os.path.dirname(__file__), '..', 'backend', 'shuttle.db')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')

def main():
    print("🔄 Creating database backup...")
    
    if not os.path.exists(DATABASE):
        print("❌ Database not found!")
        return
    
    # Create backup directory
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"shuttle_backup_{timestamp}.db")
    
    # Copy database
    shutil.copy2(DATABASE, backup_file)
    
    print(f"✅ Backup created: {backup_file}")
    print(f"   Size: {os.path.getsize(backup_file)} bytes")

if __name__ == "__main__":
    main()