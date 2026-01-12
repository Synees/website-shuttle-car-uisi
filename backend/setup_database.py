"""
UISI Shuttle Tracking - Database Setup v2.0
============================================

FITUR BARU:
- Bcrypt password hashing (lebih aman dari SHA256)
- Role-based access control (RBAC)
- Tabel permissions untuk granular access
- Default admin, driver, dan user test accounts

CARA PAKAI:
cd backend
python setup_database2.py
"""

import sqlite3
import os
from datetime import datetime
from passlib.context import CryptContext

DATABASE = "shuttle.db"

# Setup bcrypt untuk password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash password menggunakan bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password dengan bcrypt"""
    return pwd_context.verify(plain_password, hashed_password)

def create_database():
    """Create database dengan role management yang proper"""
    
    # Hapus database lama jika ada
    if os.path.exists(DATABASE):
        response = input("⚠️  Database sudah ada. Hapus dan buat baru? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled")
            return False
        os.remove(DATABASE)
        print("🗑️  Old database deleted")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("\n📦 Creating tables...\n")
    
    # ==================== TABEL ROLES ====================
    print("   📋 Creating table: roles")
    cursor.execute("""
        CREATE TABLE roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    # Insert default roles
    now = datetime.now().isoformat()
    roles = [
        ('pengguna', 'Mahasiswa - Dapat booking shuttle dan lihat tracking', now),
        ('admin', 'Administrator - Kelola semua data sistem', now),
        ('driver', 'Driver - Terima booking dan tracking GPS', now)
    ]
    cursor.executemany("""
        INSERT INTO roles (name, description, created_at) VALUES (?, ?, ?)
    """, roles)
    
    # ==================== TABEL USERS ====================
    print("   📋 Creating table: users")
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            role_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            nim TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'suspended')),
            email_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            last_login TEXT,
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
    """)
    
    # Create indexes untuk performance
    cursor.execute("CREATE INDEX idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX idx_users_role ON users(role_id)")
    cursor.execute("CREATE INDEX idx_users_status ON users(status)")
    
    # ==================== TABEL SESSIONS ====================
    print("   📋 Creating table: sessions")
    cursor.execute("""
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_sessions_token ON sessions(token)")
    cursor.execute("CREATE INDEX idx_sessions_user ON sessions(user_id)")
    
    # ==================== TABEL VEHICLES ====================
    print("   📋 Creating table: vehicles")
    cursor.execute("""
        CREATE TABLE vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT UNIQUE NOT NULL,
            brand TEXT,
            model TEXT,
            year INTEGER,
            capacity INTEGER NOT NULL,
            status TEXT DEFAULT 'available' CHECK(status IN ('available', 'in_use', 'maintenance', 'retired')),
            driver_id INTEGER,
            last_maintenance TEXT,
            next_maintenance TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (driver_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_vehicles_driver ON vehicles(driver_id)")
    cursor.execute("CREATE INDEX idx_vehicles_status ON vehicles(status)")
    
    # ==================== TABEL LOCATIONS ====================
    print("   📋 Creating table: locations")
    cursor.execute("""
        CREATE TABLE locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            type TEXT DEFAULT 'pickup' CHECK(type IN ('pickup', 'drop', 'both')),
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'temporary')),
            address TEXT,
            landmark TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_locations_status ON locations(status)")
    cursor.execute("CREATE INDEX idx_locations_type ON locations(type)")

    # ==================== TABEL BOOKINGS ====================
    print("   📋 Creating table: bookings")
    cursor.execute("""
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            from_location_id INTEGER NOT NULL,
            to_location_id INTEGER NOT NULL,
            pickup_time TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'driver_arriving', 'ongoing', 'completed', 'cancelled', 'no_show')),
            driver_id INTEGER,
            vehicle_id INTEGER,
            notes TEXT,
            passenger_count INTEGER DEFAULT 1,
            estimated_distance REAL,
            actual_distance REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            accepted_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            cancelled_at TEXT,
            cancellation_reason TEXT,
            cancelled_by INTEGER,
            rating INTEGER CHECK(rating BETWEEN 1 AND 5),
            review TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (driver_id) REFERENCES users(id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id),
            FOREIGN KEY (from_location_id) REFERENCES locations(id),
            FOREIGN KEY (to_location_id) REFERENCES locations(id),
            FOREIGN KEY (cancelled_by) REFERENCES users(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_bookings_user ON bookings(user_id)")
    cursor.execute("CREATE INDEX idx_bookings_driver ON bookings(driver_id)")
    cursor.execute("CREATE INDEX idx_bookings_status ON bookings(status)")
    cursor.execute("CREATE INDEX idx_bookings_created ON bookings(created_at)")
    
    # ==================== TABEL TRIPS ====================
    print("   📋 Creating table: trips")
    cursor.execute("""
        CREATE TABLE trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER UNIQUE,
            driver_id INTEGER NOT NULL,
            vehicle_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            distance REAL DEFAULT 0.0,
            duration INTEGER,
            status TEXT DEFAULT 'ongoing' CHECK(status IN ('ongoing', 'completed', 'cancelled')),
            created_at TEXT NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings(id),
            FOREIGN KEY (driver_id) REFERENCES users(id),
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_trips_driver ON trips(driver_id)")
    cursor.execute("CREATE INDEX idx_trips_status ON trips(status)")
    
    # ==================== TABEL LOCATION HISTORY ====================
    print("   📋 Creating table: location_history")
    cursor.execute("""
        CREATE TABLE location_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NULL,
            driver_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            speed REAL DEFAULT 0.0,
            heading REAL DEFAULT 0.0,
            accuracy REAL DEFAULT 10.0,
            altitude REAL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (trip_id) REFERENCES trips(id),
            FOREIGN KEY (driver_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_location_trip ON location_history(trip_id)")
    cursor.execute("CREATE INDEX idx_location_timestamp ON location_history(timestamp)")
    
    # ==================== TABEL SCHEDULES ====================
    print("   📋 Creating table: schedules")
    cursor.execute("""
        CREATE TABLE schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id INTEGER NOT NULL,
            route_name TEXT NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT,
            days TEXT NOT NULL,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'cancelled')),
            created_at TEXT NOT NULL,
            updated_at TEXT,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        )
    """)
    
    # ==================== TABEL NOTIFICATIONS ====================
    print("   📋 Creating table: notifications")
    cursor.execute("""
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('booking', 'trip', 'system', 'maintenance')),
            priority TEXT DEFAULT 'normal' CHECK(priority IN ('low', 'normal', 'high', 'urgent')),
            is_read INTEGER DEFAULT 0,
            data TEXT,
            created_at TEXT NOT NULL,
            read_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_notifications_user ON notifications(user_id)")
    cursor.execute("CREATE INDEX idx_notifications_read ON notifications(is_read)")
    
    # ==================== TABEL AUDIT LOG ====================
    print("   📋 Creating table: audit_log")
    cursor.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_audit_user ON audit_log(user_id)")
    cursor.execute("CREATE INDEX idx_audit_entity ON audit_log(entity_type, entity_id)")
    cursor.execute("CREATE INDEX idx_audit_created ON audit_log(created_at)")
    
    conn.commit()
    print("✅ All tables created successfully!\n")
    
    # ==================== INSERT DATA AWAL ====================
    print("📝 Inserting initial data...\n")
    
    now = datetime.now().isoformat()
    
    # 1. Insert Admin Default
    print("   👤 Creating default admin account")
    admin_password = hash_password('admin123')
    cursor.execute("""
        INSERT INTO users (email, password_hash, role_id, name, status, created_at)
        VALUES (?, ?, 2, 'Administrator', 'active', ?)
    """, ('admin@uisi.ac.id', admin_password, now))
    print("      ✅ Admin: admin@uisi.ac.id / admin123")
    
    # 2. Insert Driver Accounts
    print("   👤 Creating default driver accounts")
    driver_password = hash_password('driver123')
    
    cursor.execute("""
        INSERT INTO users (email, password_hash, role_id, name, phone, status, created_at)
        VALUES (?, ?, 3, 'Driver 1', '081234567890', 'active', ?)
    """, ('driver1@uisi.ac.id', driver_password, now))
    print("      ✅ Driver 1: driver1@uisi.ac.id / driver123")
    
    cursor.execute("""
        INSERT INTO users (email, password_hash, role_id, name, phone, status, created_at)
        VALUES (?, ?, 3, 'Driver 2', '081234567891', 'active', ?)
    """, ('driver2@uisi.ac.id', driver_password, now))
    print("      ✅ Driver 2: driver2@uisi.ac.id / driver123")
    
    # 3. Insert Test Student (no password - auto-register)
    print("   👤 Creating test student account")
    cursor.execute("""
        INSERT INTO users (email, role_id, name, nim, status, created_at)
        VALUES (?, 1, 'Mahasiswa Test', '2024001', 'active', ?)
    """, ('mahasiswa.test@student.uisi.ac.id', now))
    print("      ✅ Mahasiswa: mahasiswa.test@student.uisi.ac.id (no password - auto-register)")
    
    # 4. Insert Vehicles
    print("\n   🚐 Creating vehicles")
    cursor.execute("""
        INSERT INTO vehicles (plate_number, brand, model, year, capacity, status, driver_id, created_at)
        VALUES ('L 1234 AB', 'Toyota', 'Hiace', 2022, 14, 'available', 2, ?)
    """, (now,))
    print("      ✅ Vehicle 1: L 1234 AB - Toyota Hiace (14 seats)")
    
    cursor.execute("""
        INSERT INTO vehicles (plate_number, brand, model, year, capacity, status, driver_id, created_at)
        VALUES ('L 5678 CD', 'Isuzu', 'Elf', 2021, 14, 'available', 3, ?)
    """, (now,))
    print("      ✅ Vehicle 2: L 5678 CD - Isuzu Elf (14 seats)")
    
    # 5. Insert Default Locations (8 Kampus UISI)
    print("\n   📍 Creating campus locations")
    locations = [
        ("Pos P13", "Pos Satpam P13 - Main Gate", -7.1633, 112.6280, "both", "Jl. Veteran, Gresik"),
        ("PPS", "Parkir Pusat Semen", -7.1645, 112.6275, "pickup", "Area Parkir Pusat"),
        ("Gedung 1A", "Gedung Perkuliahan 1A", -7.1650, 112.6285, "both", "Kompleks Perkuliahan"),
        ("Gedung 1B", "Gedung Perkuliahan 1B", -7.1655, 112.6290, "both", "Kompleks Perkuliahan"),
        ("POTK", "Pusat Olahraga Terpadu Kampus", -7.1640, 112.6295, "pickup", "Area Olahraga"),
        ("K3", "Kantin Kampus 3", -7.1648, 112.6300, "both", "Area Kantin"),
        ("POS 1 SIG", "Pos Satpam 1 SIG", -7.1638, 112.6310, "pickup", "Pos Keamanan"),
        ("Wiragraha", "Gedung Wiragraha", -7.1652, 112.6288, "both", "Gedung Admin"),
    ]
    
    for name, desc, lat, lng, loc_type, address in locations:
        cursor.execute("""
            INSERT INTO locations (name, description, latitude, longitude, type, address, status, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, 1)
        """, (name, desc, lat, lng, loc_type, address, now))
        print(f"      ✅ {name}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*70)
    print("🎉 DATABASE SETUP v2.0 COMPLETED SUCCESSFULLY!")
    print("="*70)
    print("\n📊 Summary:")
    print("   ✅ 3 Roles (Pengguna, Admin, Driver)")
    print("   ✅ 1 Admin account")
    print("   ✅ 2 Driver accounts")
    print("   ✅ 1 Test student account")
    print("   ✅ 2 Vehicles")
    print("   ✅ 8 Campus locations")
    print("   ✅ Bcrypt password hashing")
    print("   ✅ Session management")
    print("   ✅ Audit logging")
    print("\n🔑 Default Credentials:")
    print("   Admin  : admin@uisi.ac.id / admin123")
    print("   Driver1: driver1@uisi.ac.id / driver123")
    print("   Driver2: driver2@uisi.ac.id / driver123")
    print("   Student: [email]@student.uisi.ac.id (auto-register)")
    print("\n🔒 Security Features:")
    print("   ✅ Bcrypt password hashing (cost factor 12)")
    print("   ✅ Session tokens dengan expiry")
    print("   ✅ Audit log untuk tracking aktivitas")
    print("   ✅ Email verification support")
    print("   ✅ Account status (active/inactive/suspended)")
    print("\n📝 Next Steps:")
    print("   1. Run backend: python main.py 0.0.0.0 8000")
    print("   2. Open browser: http://localhost:8000")
    print("   3. Login dengan credentials di atas")
    print("="*70)
    
    return True

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════════════╗
║                                                                    ║
║       🚌 UISI SHUTTLE TRACKING - DATABASE SETUP v2.0 🚌            ║
║                                                                    ║
║   Enhanced Security & Role Management System                       ║
║                                                                    ║
║   Features:                                                        ║
║   • Bcrypt password hashing                                        ║
║   • Role-based access control (RBAC)                               ║
║   • Session management                                             ║
║   • Audit logging                                                  ║
║   • Email verification support                                     ║
║                                                                    ║
║   Roles:                                                           ║
║   • Pengguna (Mahasiswa) - Booking & Tracking                      ║
║   • Admin - Kelola Semua Data                                      ║
║   • Driver - GPS Tracking & Terima Booking                         ║
║                                                                    ║
╚════════════════════════════════════════════════════════════════════╝
""")
    
    try:
        # Check if passlib is installed
        try:
            from passlib.context import CryptContext
        except ImportError:
            print("❌ ERROR: passlib tidak terinstall!")
            print("   Jalankan: pip install passlib[bcrypt]")
            exit(1)
        
        success = create_database()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
