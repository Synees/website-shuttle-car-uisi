"""
Update GPS Coordinates
======================

INSTRUKSI:
Script ini untuk update koordinat GPS lokasi kampus yang real.

CARA PAKAI:
1. Buka Google Maps
2. Cari setiap lokasi kampus UISI
3. Klik kanan → "What's here?"
4. Copy koordinat yang muncul
5. Update di section KOORDINAT BARU di bawah
6. Jalankan: python update_coordinates.py

CONTOH:
Jika di Google Maps terlihat:
Pos P13: -7.1633, 112.6280

Maka update di bawah:
    "Pos P13": (-7.1633, 112.6280),
"""

import sqlite3
import sys
import os

# Path ke database (adjust jika perlu)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
DATABASE = os.path.join(os.path.dirname(__file__), '..', 'backend', 'shuttle.db')

# ============================================
# UPDATE KOORDINAT BARU DI SINI!
# ============================================
# Format: "Nama Lokasi": (latitude, longitude)

KOORDINAT_BARU = {
    # CONTOH - Ganti dengan koordinat real dari Google Maps!
    # "Pos P13": (-7.1633, 112.6280),
    # "PPS": (-7.1645, 112.6275),
    # "Ged 1 A": (-7.1650, 112.6285),
    # "Ged 1 B": (-7.1655, 112.6290),
    # "POTK": (-7.1640, 112.6295),
    # "K3": (-7.1648, 112.6300),
    # "POS 1 SIG": (-7.1638, 112.6310),
    # "Wiragraha": (-7.1652, 112.6288),
    
    # Uncomment dan update koordinat di atas!
    # Atau tambahkan satu per satu seperti ini:
    # "Pos P13": (-7.XXXX, 112.XXXX),
}

# ============================================

def update_location(conn, location_name, new_lat, new_lng):
    """Update koordinat untuk satu lokasi"""
    cursor = conn.cursor()
    
    # Update berdasarkan nama lokasi (LIKE untuk partial match)
    cursor.execute("""
        UPDATE routes 
        SET latitude = ?, longitude = ?
        WHERE location_name LIKE ?
    """, (new_lat, new_lng, f"{location_name}%"))
    
    rows_affected = cursor.rowcount
    
    if rows_affected > 0:
        print(f"  ✅ Updated: {location_name}")
        print(f"     New coordinates: ({new_lat}, {new_lng})")
        return True
    else:
        print(f"  ⚠️  Location not found: {location_name}")
        return False

def show_current_coordinates(conn):
    """Tampilkan koordinat saat ini"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT location_name, latitude, longitude 
        FROM routes 
        ORDER BY point_order
    """)
    
    print("\n" + "="*70)
    print("KOORDINAT SAAT INI:")
    print("="*70)
    
    for row in cursor.fetchall():
        name = row[0].split(" - ")[0] if " - " in row[0] else row[0]
        print(f"{name:15} : ({row[1]}, {row[2]})")
    
    print("="*70)

def main():
    """Main function"""
    
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       📍 UPDATE GPS COORDINATES - UISI SHUTTLE 📍         ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")
    
    # Check database exists
    if not os.path.exists(DATABASE):
        print(f"❌ Database not found: {DATABASE}")
        print("   Please run setup_database.py first!")
        return False
    
    try:
        # Connect to database
        print(f"🔌 Connecting to database: {DATABASE}")
        conn = sqlite3.connect(DATABASE)
        
        # Show current coordinates
        show_current_coordinates(conn)
        
        # Check if ada koordinat baru
        if not KOORDINAT_BARU:
            print("\n⚠️  TIDAK ADA KOORDINAT UNTUK DI-UPDATE!")
            print("\nCara update:")
            print("1. Edit file ini: scripts/update_coordinates.py")
            print("2. Uncomment dan isi KOORDINAT_BARU")
            print("3. Jalankan lagi script ini")
            print("\nContoh:")
            print('KOORDINAT_BARU = {')
            print('    "Pos P13": (-7.1633, 112.6280),')
            print('    "Ged 1 A": (-7.1650, 112.6285),')
            print('}')
            conn.close()
            return False
        
        # Update coordinates
        print(f"\n🔄 Updating {len(KOORDINAT_BARU)} locations...")
        print("-" * 70)
        
        updated_count = 0
        for location_name, (lat, lng) in KOORDINAT_BARU.items():
            if update_location(conn, location_name, lat, lng):
                updated_count += 1
        
        # Commit changes
        if updated_count > 0:
            conn.commit()
            print("-" * 70)
            print(f"\n✅ Successfully updated {updated_count} location(s)")
            
            # Show updated coordinates
            show_current_coordinates(conn)
            
            print("\n🎉 UPDATE COMPLETED!")
            print("\nNext steps:")
            print("1. Restart backend: python main.py")
            print("2. Test di frontend untuk verify posisi")
        else:
            print("\n⚠️  No locations were updated")
        
        # Close connection
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)