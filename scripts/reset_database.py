"""
Reset Database
==============

INSTRUKSI:
Script ini untuk reset database (hapus semua data).
HATI-HATI! Semua data akan hilang!

KAPAN PAKAI:
- Saat ada error database
- Mau mulai dari awal
- Testing

CARA PAKAI:
python reset_database.py
"""

import sqlite3
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
DATABASE = os.path.join(os.path.dirname(__file__), '..', 'backend', 'shuttle.db')

def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       ⚠️  RESET DATABASE - UISI SHUTTLE ⚠️                ║
║                                                            ║
║   WARNING: This will DELETE ALL DATA!                      ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")
    
    if not os.path.exists(DATABASE):
        print("✅ Database doesn't exist. Nothing to reset.")
        return
    
    # Confirmation
    print(f"\nDatabase: {DATABASE}")
    response = input("\nAre you sure you want to DELETE ALL DATA? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled. No changes made.")
        return
    
    try:
        # Delete database file
        os.remove(DATABASE)
        print("\n✅ Database deleted successfully!")
        print("\nNext steps:")
        print("1. Run: cd ../backend && python setup_database.py")
        print("2. Run: python main.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()