"""
Setup Database & Rute UISI
==========================

INSTRUKSI:
1. Jalankan script ini PERTAMA KALI sebelum main.py
2. Script ini akan:
   - Create database SQLite
   - Create semua tables
   - Insert 8 lokasi kampus UISI
   - Insert shuttle info
3. Setelah selesai, jalankan main.py

CARA JALANKAN:
python setup_database.py

CATATAN PENTING:
⚠️ Koordinat GPS yang digunakan adalah ESTIMASI
⚠️ Anda HARUS update dengan koordinat real menggunakan:
   cd ../scripts
   python update_coordinates.py

Cara cari koordinat real:
1. Buka Google Maps
2. Cari "UISI Gresik" atau alamat lengkap kampus
3. Klik kanan pada setiap lokasi → "What's here?"
4. Copy koordinat (contoh: -7.1633, 112.6280)
5. Update di update_coordinates.py
"""

import sqlite3
from datetime import datetime

DATABASE = "shuttle.db"

# Koordinat GPS untuk lokasi UISI
# ⚠️ INI ADALAH ESTIMASI - HARUS DI-UPDATE!
UISI_LOCATIONS = {
    "Pos P13": {
        "lat": -7.1633,
        "lng": 112.6280,
        "description": "Pos Security P13 - Pintu Masuk Utama"
    },
    "PPS": {
        "lat": -7.1645,
        "lng": 112.6275,
        "description": "Gedung Pascasarjana (PPS)"
    },
    "Ged 1 A": {
        "lat": -7.1650,
        "lng": 112.6285,
        "description": "Gedung 1 A - Gedung Kuliah"
    },
    "Ged 1 B": {
        "lat": -7.1655,
        "lng": 112.6290,
        "description": "Gedung 1 B - Gedung Kuliah"
    },
    "POTK": {
        "lat": -7.1640,
        "lng": 112.6295,
        "description": "Pusat Olahraga dan Teknologi Kebugaran"
    },
    "K3": {
        "lat": -7.1648,
        "lng": 112.6300,
        "description": "Kantor K3 (Kesehatan dan Keselamatan Kerja)"
    },
    "POS 1 SIG": {
        "lat": -7.1638,
        "lng": 112.6310,
        "description": "Pos Security 1 SIG"
    },
    "Wiragraha": {
        "lat": -7.1652,
        "lng": 112.6288,
        "description": "Gedung Wiragraha"
    }
}

def create_tables(cursor):
    """Create semua tables yang dibutuhkan"""
    
    print("📝 Creating tables...")
    
    # Shuttles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shuttles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT DEFAULT 'inactive',
            total_distance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✅ Table: shuttles")
    
    # Routes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shuttle_id INTEGER DEFAULT 1,
            point_order INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            location_name TEXT NOT NULL,
            FOREIGN KEY (shuttle_id) REFERENCES shuttles(id)
        )
    """)
    print("  ✅ Table: routes")
    
    # Location history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS location_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shuttle_id INTEGER DEFAULT 1,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            speed REAL DEFAULT 0,
            heading REAL DEFAULT 0,
            accuracy REAL DEFAULT 10,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shuttle_id) REFERENCES shuttles(id)
        )
    """)
    print("  ✅ Table: location_history")
    
    # Trips table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shuttle_id INTEGER DEFAULT 1,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            distance REAL DEFAULT 0,
            status TEXT DEFAULT 'ongoing',
            FOREIGN KEY (shuttle_id) REFERENCES shuttles(id)
        )
    """)
    print("  ✅ Table: trips")
    
    # Route requests table (NEW - untuk flexible routing)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS route_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shuttle_id INTEGER DEFAULT 1,
            from_location TEXT NOT NULL,
            to_location TEXT NOT NULL,
            requested_by TEXT DEFAULT 'Mahasiswa',
            request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            note TEXT,
            FOREIGN KEY (shuttle_id) REFERENCES shuttles(id)
        )
    """)
    print("  ✅ Table: route_requests")
    
    # Active routes table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shuttle_id INTEGER DEFAULT 1,
            from_location TEXT NOT NULL,
            to_location TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (shuttle_id) REFERENCES shuttles(id)
        )
    """)
    print("  ✅ Table: active_routes")

def insert_shuttle_info(cursor):
    """Insert info shuttle UISI"""
    
    print("\n🚌 Setting up shuttle info...")
    
    cursor.execute("SELECT COUNT(*) as count FROM shuttles")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO shuttles (name, status) 
            VALUES ('Shuttle UISI - Alfian Putra', 'inactive')
        """)
        print("  ✅ Shuttle info created")
    else:
        print("  ℹ️  Shuttle info already exists")

def insert_locations(cursor):
    """Insert semua lokasi kampus UISI"""
    
    print("\n📍 Adding campus locations...")
    
    cursor.execute("SELECT COUNT(*) as count FROM routes")
    if cursor.fetchone()[0] == 0:
        point_order = 1
        for location_name, coords in UISI_LOCATIONS.items():
            cursor.execute("""
                INSERT INTO routes (shuttle_id, point_order, latitude, longitude, location_name)
                VALUES (?, ?, ?, ?, ?)
            """, (1, point_order, coords['lat'], coords['lng'], 
                  f"{location_name} - {coords['description']}"))
            print(f"  ✅ Added: {location_name}")
            point_order += 1
    else:
        print("  ℹ️  Locations already exist")

def show_summary():
    """Show summary setelah setup"""
    
    print("\n" + "="*60)
    print("SETUP COMPLETED! ✨")
    print("="*60)
    
    print("\n📊 LOKASI YANG TERSEDIA:")
    print("-" * 60)
    for i, (name, coords) in enumerate(UISI_LOCATIONS.items(), 1):
        print(f"{i}. {name:15} - {coords['description']}")
        print(f"   GPS: {coords['lat']}, {coords['lng']}")
    print("-" * 60)
    
    print("\n⚠️  PENTING - KOORDINAT GPS!")
    print("-" * 60)
    print("Koordinat yang digunakan adalah ESTIMASI.")
    print("Anda HARUS update dengan koordinat real:")
    print("")
    print("1. Buka Google Maps")
    print("2. Cari lokasi kampus UISI di Gresik")
    print("3. Klik kanan setiap lokasi → 'What's here?'")
    print("4. Copy koordinat (contoh: -7.1633, 112.6280)")
    print("5. Jalankan: cd ../scripts && python update_coordinates.py")
    print("-" * 60)
    
    print("\n🚀 NEXT STEPS:")
    print("-" * 60)
    print("1. Update koordinat GPS (WAJIB!)")
    print("2. Jalankan backend: python main.py")
    print("3. Buka browser: http://localhost:8000/docs")
    print("4. Test API endpoints")
    print("5. Akses frontend: http://localhost:8000/")
    print("-" * 60)
    
    print("\n📚 DOKUMENTASI:")
    print("-" * 60)
    print("- Setup Guide: ../docs/SETUP_GUIDE.md")
    print("- API Docs: http://localhost:8000/docs (setelah server jalan)")
    print("- User Guide: ../docs/USER_GUIDE.md")
    print("-" * 60)
    
    print("\n✅ Database ready! You can now run: python main.py")
    print("="*60)

def main():
    """Main setup function"""
    
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       🚌 UISI SHUTTLE TRACKING - DATABASE SETUP 🚌        ║
║                                                            ║
║   Universitas Internasional Semen Indonesia                ║
║   Gresik, Jawa Timur                                       ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        print("  ✅ Connected\n")
        
        # Create tables
        create_tables(cursor)
        
        # Insert shuttle info
        insert_shuttle_info(cursor)
        
        # Insert locations
        insert_locations(cursor)
        
        # Commit changes
        conn.commit()
        print("\n💾 Changes saved to database")
        
        # Close connection
        conn.close()
        print("🔌 Database connection closed")
        
        # Show summary
        show_summary()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting:")
        print("- Pastikan Python sudah terinstall")
        print("- Pastikan SQLite tersedia (built-in di Python)")
        print("- Check permissions folder ini")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)