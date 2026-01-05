import os
import sys
import math
import secrets
import sqlite3
from contextlib import contextmanager, asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Callable
import uvicorn
from passlib.context import CryptContext
from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Header,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from fastapi import UploadFile, File
from fastapi.responses import Response
import shutil

# === CONFIG ===
# DATABASE: ./backend/shuttle.db
# ASSETS:   ./assets
# SCHEDULE: ./assets/jadwal.pdf

PROJECT_ROOT = os.path.dirname(__file__)
DATABASE = os.path.join(PROJECT_ROOT, "backend", "shuttle.db")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
SCHEDULE_PATH = os.path.join(ASSETS_DIR, "jadwal.pdf")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
os.makedirs(ASSETS_DIR, exist_ok=True)

print("PROJECT_ROOT :", PROJECT_ROOT)
print("DATABASE     :", DATABASE)
print("ASSETS_DIR   :", ASSETS_DIR)
print("SCHEDULE_PATH:", SCHEDULE_PATH)
print()

# === MODELS ===
class LoginRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None

class BookingRequest(BaseModel):
    from_location_id: int
    to_location_id: int
    notes: Optional[str] = None
    passenger_count: int = 1

class LocationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    type: str = "pickup"
    address: Optional[str] = None

class VehicleCreate(BaseModel):
    plate_number: str
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    capacity: int
    driver_id: Optional[int] = None

class LocationData(BaseModel):
    latitude: float
    longitude: float
    speed: float = 0.0
    heading: float = 0.0
    accuracy: float = 10.0
    altitude: Optional[float] = None

class BookingStatusUpdate(BaseModel):
    status: str

# ==================== DATABASE CONTEXT ====================

@contextmanager
def get_db():
    # Use check_same_thread=False to allow usage from multiple threads (uvicorn workers)
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

# ==================== UTILITIES ====================

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad)*math.cos(lat2_rad)*math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def log_audit(conn, user_id: int, action: str, entity_type: str, entity_id: int = None,
              old_value: str = None, new_value: str = None, ip: str = None):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_value, new_value, ip_address, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, action, entity_type, entity_id, old_value, new_value, ip, datetime.now().isoformat()))
    conn.commit()

# ==================== AUTH DEPENDENCIES ====================

async def get_current_user(authorization: Optional[str] = Header(None)) -> Tuple[int, str]:
    """
    Validate Bearer token and return (user_id, role_name).
    Raises 401 when not authenticated.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "", 1)
    now_iso = datetime.now().isoformat()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.user_id, u.email, r.name as role, u.status
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            JOIN roles r ON u.role_id = r.id
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, now_iso))
        session = cursor.fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        if session["status"] != "active":
            raise HTTPException(status_code=403, detail="Account is not active")

        return (session["user_id"], session["role"])

def require_role(*allowed_roles: str) -> Callable:
    """
    Returns a dependency that checks whether current user's role is allowed.
    Usage: Depends(require_role("admin"))
    """
    async def role_checker(user_data: Tuple[int, str] = Depends(get_current_user)):
        user_id, role = user_data
        if role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Access denied. Required role: {', '.join(allowed_roles)}")
        return user_id
    return role_checker

# ==================== WEBSOCKET MANAGER ====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.driver_connections: dict = {}

    async def connect(self, websocket: WebSocket, user_id: int = None, role: str = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if role == "driver" and user_id:
            self.driver_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for driver_id, ws in list(self.driver_connections.items()):
            if ws == websocket:
                del self.driver_connections[driver_id]

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except:
                dead_connections.append(connection)
        for conn in dead_connections:
            self.disconnect(conn)

    async def send_to_driver(self, driver_id: int, message: dict):
        ws = self.driver_connections.get(driver_id)
        if ws:
            try:
                await ws.send_json(message)
            except:
                # ignore send errors; do not crash caller
                pass

manager = ConnectionManager()

# ==================== FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(DATABASE):
        print("⚠️  WARNING: Database not found! Run: python backend/setup_database2.py")

app = FastAPI(
    title="UISI Shuttle Tracking API v2.0",
    description="Secure shuttle tracking system with role-based access control",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount static only if directory exists
static_dir = os.path.join(PROJECT_ROOT, "frontend", "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"⚠️ Static directory not found: {static_dir} (skipping mount)")

# ==================== AUTH ENDPOINTS ====================

@app.post("/api/auth/login")
async def login(request: LoginRequest, req: Request):
    """
    Login endpoint:
    - Mahasiswa: email @student.uisi.ac.id (auto-register, no password)
    - Admin/Driver: email + password (bcrypt)
    """
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT u.*, r.name as role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.email = ?
        """, (request.email,))
        user = cursor.fetchone()

        if not user and request.email.endswith("@student.uisi.ac.id"):
            # auto-register mahasiswa (pengguna)
            name_guess = request.email.split("@")[0]
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO users (email, role_id, name, status, created_at)
                VALUES (?, 1, ?, 'active', ?)
            """, (request.email, name_guess, now))
            conn.commit()
            user_id = cursor.lastrowid
            role_name = "pengguna"
            try:
                client_ip = req.client.host
            except:
                client_ip = None
            log_audit(conn, user_id, "register", "user", user_id, None, None, client_ip)
        elif not user:
            raise HTTPException(status_code=404, detail="User not found")
        else:
            user_id = user["id"]
            role_name = user["role_name"]

            if role_name in ["admin", "driver"]:
                if not request.password:
                    raise HTTPException(status_code=400, detail="Password required for admin/driver")
                if not user["password_hash"]:
                    raise HTTPException(status_code=500, detail="User has no password set")
                if not verify_password(request.password, user["password_hash"]):
                    try:
                        client_ip = req.client.host
                    except:
                        client_ip = None
                    log_audit(conn, user_id, "login_failed", "user", user_id, None, "Invalid password", client_ip)
                    raise HTTPException(status_code=401, detail="Invalid password")

            if user["status"] != "active":
                raise HTTPException(status_code=403, detail=f"Account is {user['status']}")

        # Create session token and persist
        token = generate_token()
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()
        try:
            client_ip = req.client.host
        except:
            client_ip = None

        cursor.execute("""
            INSERT INTO sessions (user_id, token, ip_address, user_agent, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, token, client_ip, req.headers.get("user-agent"), expires_at, datetime.now().isoformat()))
        conn.commit()  # ensure session persisted

        # Update last login
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.now().isoformat(), user_id))
        conn.commit()

        try:
            cursor.execute("""
                SELECT u.id, u.email, u.name, u.nim, u.phone, r.name as role
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = ?
            """, (user_id,))
            user_info = cursor.fetchone()
            user_dict = dict(user_info) if user_info else {"id": user_id, "email": request.email, "role": role_name}
        except Exception:
            user_dict = {"id": user_id, "email": request.email, "role": role_name}

        log_audit(conn, user_id, "login", "user", user_id, None, None, client_ip)

        return {
            "success": True,
            "token": token,
            "expires_at": expires_at,
            "user": user_dict
        }

@app.post("/api/auth/logout")
async def logout(user_id: int = Depends(require_role("pengguna", "admin", "driver")), authorization: str = Header(None)):
    """Logout - hapus session"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.replace("Bearer ", "", 1)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        log_audit(conn, user_id, "logout", "user", user_id)
        conn.commit()

    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/auth/me")
async def get_current_user_info(user_data: Tuple = Depends(get_current_user)):
    """Get current user info"""
    user_id, role = user_data

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, u.name, u.nim, u.phone, u.status, r.name as role
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?
        """, (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user)

# ==================== PENGGUNA ENDPOINTS ====================

@app.post("/api/bookings")
async def create_booking(booking: BookingRequest, user_id: int = Depends(require_role("pengguna")), req: Request = None):
    """Pengguna: Buat booking baru"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM locations WHERE id IN (?, ?) AND status = 'active'",
                       (booking.from_location_id, booking.to_location_id))
        rows = cursor.fetchall()
        if len(rows) != 2:
            raise HTTPException(status_code=404, detail="Invalid or inactive location")

        booking_code = f"SHU{datetime.now().strftime('%Y%m%d')}{secrets.token_hex(3).upper()}"

        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO bookings (booking_code, user_id, from_location_id, to_location_id, notes, passenger_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (booking_code, user_id, booking.from_location_id, booking.to_location_id,
              booking.notes, booking.passenger_count, now))
        booking_id = cursor.lastrowid

        # Try to auto-assign driver
        cursor.execute("""
            SELECT u.id as id, u.name as name, v.id as vehicle_id FROM users u
            JOIN vehicles v ON v.driver_id = u.id
            JOIN roles r ON u.role_id = r.id
            WHERE r.name = 'driver' AND u.status = 'active' AND v.status = 'available'
            LIMIT 1
        """)
        driver = cursor.fetchone()

        if driver:
            cursor.execute("""
                UPDATE bookings SET driver_id = ?, vehicle_id = ?, status = 'accepted', accepted_at = ?
                WHERE id = ?
            """, (driver["id"], driver["vehicle_id"], now, booking_id))

            cursor.execute("""
                INSERT INTO notifications (user_id, title, message, type, priority, created_at)
                VALUES (?, 'Booking Baru', ?, 'booking', 'high', ?)
            """, (driver["id"], f"Booking baru #{booking_code}", now))

            # Safe websocket send
            try:
                await manager.send_to_driver(driver["id"], {
                    "type": "new_booking",
                    "booking_id": booking_id,
                    "booking_code": booking_code
                })
            except Exception:
                pass

        try:
            client_ip = req.client.host if req and req.client else None
        except:
            client_ip = None
        log_audit(conn, user_id, "create", "booking", booking_id, None, booking_code, client_ip)
        conn.commit()

        return {
            "success": True,
            "booking_id": booking_id,
            "booking_code": booking_code,
            "status": "accepted" if driver else "pending",
            "message": "Booking berhasil dibuat"
        }

@app.get("/api/bookings/my")
async def get_my_bookings(user_id: int = Depends(require_role("pengguna"))):
    """Pengguna: Lihat booking sendiri"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*,
                   l1.name as from_location_name,
                   l2.name as to_location_name,
                   d.name as driver_name, d.phone as driver_phone
            FROM bookings b
            JOIN locations l1 ON b.from_location_id = l1.id
            JOIN locations l2 ON b.to_location_id = l2.id
            LEFT JOIN users d ON b.driver_id = d.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

@app.put("/api/bookings/{booking_id}/cancel")
async def cancel_booking(booking_id: int, user_id: int = Depends(require_role("pengguna")), req: Request = None):
    """Pengguna: Batalkan booking"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id = ? AND user_id = ?", (booking_id, user_id))
        booking = cursor.fetchone()

        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        if booking["status"] not in ["pending", "accepted"]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel booking with status: {booking['status']}")

        cursor.execute("""
            UPDATE bookings
            SET status = 'cancelled', cancelled_at = ?, cancelled_by = ?, cancellation_reason = 'Cancelled by user'
            WHERE id = ?
        """, (datetime.now().isoformat(), user_id, booking_id))

        try:
            client_ip = req.client.host if req and req.client else None
        except:
            client_ip = None
        log_audit(conn, user_id, "cancel", "booking", booking_id, booking["status"], "cancelled", client_ip)
        conn.commit()

        return {"success": True, "message": "Booking cancelled"}

@app.get("/api/locations")
async def get_locations():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM locations WHERE status = 'active' ORDER BY name")
        return [dict(row) for row in cursor.fetchall()]

# ==================== ADMIN ENDPOINTS ====================

@app.post("/api/admin/locations")
async def create_location(location: LocationCreate, user_id: int = Depends(require_role("admin")), req: Request = None):
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO locations (name, description, latitude, longitude, type, address, status, created_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """, (location.name, location.description, location.latitude, location.longitude,
              location.type, location.address, now, user_id))

        location_id = cursor.lastrowid
        try:
            client_ip = req.client.host if req and req.client else None
        except:
            client_ip = None
        log_audit(conn, user_id, "create", "location", location_id, None, location.name, client_ip)
        conn.commit()

        return {"success": True, "location_id": location_id}

@app.put("/api/admin/locations/{location_id}")
async def update_location(location_id: int, location: LocationCreate, user_id: int = Depends(require_role("admin")), req: Request = None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM locations WHERE id = ?", (location_id,))
        old = cursor.fetchone()

        cursor.execute("""
            UPDATE locations
            SET name = ?, description = ?, latitude = ?, longitude = ?, type = ?, address = ?, updated_at = ?
            WHERE id = ?
        """, (location.name, location.description, location.latitude, location.longitude,
              location.type, location.address, datetime.now().isoformat(), location_id))

        try:
            client_ip = req.client.host if req and req.client else None
        except:
            client_ip = None
        log_audit(conn, user_id, "update", "location", location_id, old["name"] if old else None, location.name, client_ip)
        conn.commit()
        return {"success": True}

@app.delete("/api/admin/locations/{location_id}")
async def delete_location(location_id: int, user_id: int = Depends(require_role("admin")), req: Request = None):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE locations SET status = 'inactive', updated_at = ? WHERE id = ?",
                       (datetime.now().isoformat(), location_id))
        try:
            client_ip = req.client.host if req and req.client else None
        except:
            client_ip = None
        log_audit(conn, user_id, "delete", "location", location_id, None, None, client_ip)
        conn.commit()
        return {"success": True}

@app.get("/api/admin/bookings")
async def get_all_bookings(user_id: int = Depends(require_role("admin"))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*,
                   u.name as user_name, u.email as user_email, u.nim, u.phone as user_phone,
                   l1.name as from_location_name,
                   l2.name as to_location_name,
                   d.name as driver_name, d.phone as driver_phone,
                   v.plate_number
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN locations l1 ON b.from_location_id = l1.id
            JOIN locations l2 ON b.to_location_id = l2.id
            LEFT JOIN users d ON b.driver_id = d.id
            LEFT JOIN vehicles v ON b.vehicle_id = v.id
            ORDER BY b.created_at DESC
            LIMIT 100
        """)
        return [dict(row) for row in cursor.fetchall()]

@app.get("/api/admin/stats")
async def get_admin_stats(user_id: int = Depends(require_role("admin"))):
    with get_db() as conn:
        cursor = conn.cursor()
        today = datetime.now().date().isoformat()
        cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE DATE(created_at) = ?", (today,))
        today_bookings = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM bookings WHERE status = 'accepted'")
        accepted_bookings = cursor.fetchone()["count"]
        cursor.execute("SELECT COUNT(*) as count FROM users WHERE status = 'active'")
        total_users = cursor.fetchone()["count"]
        cursor.execute("""
            SELECT COUNT(*) as count FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE r.name = 'driver' AND u.status = 'active'
        """)
        total_drivers = cursor.fetchone()["count"]
        return {
            "today_bookings": today_bookings,
            "accepted_bookings": accepted_bookings,
            "total_users": total_users,
            "total_drivers": total_drivers
        }

@app.get("/api/admin/users")
async def get_all_users(user_id: int = Depends(require_role("admin"))):
    """Admin: Get all users dengan role 'pengguna' (mahasiswa)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                u.id, 
                u.email, 
                u.name, 
                u.nim, 
                u.phone,
                u.status,
                u.created_at,
                u.last_login,
                COUNT(b.id) as total_bookings
            FROM users u
            JOIN roles r ON u.role_id = r.id
            LEFT JOIN bookings b ON u.id = b.user_id
            WHERE r.name = 'pengguna'
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        
        users = cursor.fetchall()
        return [dict(row) for row in users]
    
@app.get("/api/admin/users/{user_id}/bookings")
async def get_user_bookings(user_id: int, admin_id: int = Depends(require_role("admin"))):
    """Admin: Get booking history untuk user tertentu"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user exists dan role = pengguna
        cursor.execute("""
            SELECT u.id, r.name as role
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            raise HTTPException(404, "User not found")
        
        if user["role"] != "pengguna":
            raise HTTPException(400, "This endpoint is for pengguna role only")
        
        # Get booking history
        cursor.execute("""
            SELECT 
                b.*,
                l1.name as from_location_name,
                l2.name as to_location_name,
                d.name as driver_name
            FROM bookings b
            JOIN locations l1 ON b.from_location_id = l1.id
            JOIN locations l2 ON b.to_location_id = l2.id
            LEFT JOIN users d ON b.driver_id = d.id
            WHERE b.user_id = ?
            ORDER BY b.created_at DESC
        """, (user_id,))
        
        bookings = cursor.fetchall()
        return [dict(row) for row in bookings]

@app.delete("/api/admin/users/{user_id}")
async def delete_user_account(
    user_id: int, 
    admin_id: int = Depends(require_role("admin")), 
    req: Request = None
):
    """
    Admin: Hapus user account
    
    PERINGATAN: Ini akan menghapus:
    - User account
    - Semua booking history
    - Semua session tokens
    - Audit log terkait
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Verify user exists
        cursor.execute("""
            SELECT u.id, u.email, r.name as role
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?
        """, (user_id,))
        
        user = cursor.fetchone()
        if not user:
            raise HTTPException(404, "User not found")
        
        # Prevent deleting admin/driver accounts
        if user["role"] in ["admin", "driver"]:
            raise HTTPException(403, "Cannot delete admin or driver accounts")
        
        # Delete user dan related data (CASCADE)
        try:
            # 1. Delete sessions
            cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            
            # 2. Delete notifications
            cursor.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
            
            # 3. Update bookings - set user_id to NULL atau delete
            # (Opsional: Keep booking history tapi anonymize)
            cursor.execute("""
                UPDATE bookings 
                SET status = 'cancelled',
                    cancellation_reason = 'User account deleted',
                    cancelled_by = ?,
                    cancelled_at = ?
                WHERE user_id = ? AND status NOT IN ('completed', 'cancelled')
            """, (admin_id, datetime.now().isoformat(), user_id))
            
            # 4. Delete user
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            # 5. Log audit
            log_audit(
                conn, 
                admin_id, 
                "delete_user", 
                "user", 
                user_id, 
                user["email"], 
                "deleted", 
                req.client.host
            )
            
            conn.commit()
            
            return {
                "success": True,
                "message": f"User {user['email']} berhasil dihapus"
            }
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(500, f"Failed to delete user: {str(e)}")


# ==================== SCHEDULE MANAGEMENT ENDPOINTS ====================
@app.get("/api/schedule/status")
async def get_schedule_status():
    """
    Check apakah file jadwal ada atau tidak.
    Endpoint ini bisa diakses semua role (pengguna, driver, admin)
    """
    exists = os.path.isfile(SCHEDULE_PATH)
    
    return {
        "exists": exists,
        "path": "assets/jadwal.pdf" if exists else None,
        "message": "Jadwal tersedia" if exists else "Jadwal belum diupload"
    }

@app.post("/api/admin/schedule/upload")
async def upload_schedule(
    file: UploadFile = File(...),
    user_id: int = Depends(require_role("admin")),
    req: Request = None
):
    """
    Admin: Upload file jadwal PDF
    """
    # Validasi file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File harus berformat PDF")
    
    if file.content_type != 'application/pdf':
        raise HTTPException(status_code=400, detail="File harus berformat PDF")
    
    # Validasi ukuran file (max 10MB)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()  # Get position (file size)
    file.file.seek(0)  # Reset to beginning
    
    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 10MB")
    
    try:
        # Hapus file lama jika ada
        if os.path.isfile(SCHEDULE_PATH):
            os.remove(SCHEDULE_PATH)
        
        # Simpan file baru
        with open(SCHEDULE_PATH, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Log audit
        with get_db() as conn:
            try:
                client_ip = req.client.host if req and req.client else None
            except:
                client_ip = None
            log_audit(conn, user_id, "upload", "schedule", None, None, file.filename, client_ip)
        
        return {
            "success": True,
            "message": "Jadwal berhasil diupload",
            "filename": file.filename,
            "path": "assets/jadwal.pdf"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengupload jadwal: {str(e)}")
    finally:
        file.file.close()

@app.get("/api/schedule")
async def get_schedule():
    """
    Download/View jadwal PDF.
    Endpoint ini bisa diakses semua role (pengguna, driver, admin)
    """
    if not os.path.isfile(SCHEDULE_PATH):
        raise HTTPException(
            status_code=404, 
            detail="Jadwal belum diupload oleh admin. Silakan hubungi admin untuk mengunggah jadwal."
        )
    
    return FileResponse(
        path=SCHEDULE_PATH,
        media_type="application/pdf",
        filename="Jadwal_Shuttle_UISI.pdf"
    )

@app.delete("/api/admin/schedule")
async def delete_schedule(
    user_id: int = Depends(require_role("admin")),
    req: Request = None
):
    """
    Admin: Hapus file jadwal
    """
    if not os.path.isfile(SCHEDULE_PATH):
        raise HTTPException(status_code=404, detail="File jadwal tidak ditemukan")
    
    try:
        os.remove(SCHEDULE_PATH)
        
        # Log audit
        with get_db() as conn:
            try:
                client_ip = req.client.host if req and req.client else None
            except:
                client_ip = None
            log_audit(conn, user_id, "delete", "schedule", None, "jadwal.pdf", None, client_ip)
        
        return {
            "success": True,
            "message": "Jadwal berhasil dihapus"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghapus jadwal: {str(e)}")

# ==================== DRIVER ENDPOINTS ====================
@app.get("/api/driver/bookings")
async def get_driver_bookings(user_id: int = Depends(require_role("driver"))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.*,
                   u.name as user_name, u.phone as user_phone, u.nim,
                   l1.name as from_location, l1.latitude as from_lat, l1.longitude as from_lng,
                   l2.name as to_location, l2.latitude as to_lat, l2.longitude as to_lng
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            JOIN locations l1 ON b.from_location_id = l1.id
            JOIN locations l2 ON b.to_location_id = l2.id
            WHERE b.driver_id = ? AND b.status != 'completed' AND b.status != 'cancelled'
            ORDER BY b.created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

@app.put("/api/driver/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    status_update: BookingStatusUpdate,
    user_id: int = Depends(require_role("driver")),
    req: Request = None
):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id = ? AND driver_id = ?", (booking_id, user_id))
        booking = cursor.fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found or not assigned to you")

        now = datetime.now().isoformat()
        status = status_update.status
        old_status = booking["status"]

        if status == "driver_arriving":
            cursor.execute("UPDATE bookings SET status = 'driver_arriving', updated_at = ? WHERE id = ?",
                           (now, booking_id))
        elif status == "ongoing":
            cursor.execute("UPDATE bookings SET status = 'ongoing', started_at = ?, updated_at = ? WHERE id = ?",
                           (now, now, booking_id))
            cursor.execute("SELECT id as id FROM vehicles WHERE driver_id = ?", (user_id,))
            vehicle = cursor.fetchone()
            if vehicle:
                cursor.execute("""
                    INSERT INTO trips (booking_id, driver_id, vehicle_id, start_time, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (booking_id, user_id, vehicle["id"], now, now))
        elif status == "completed":
            cursor.execute("""
                UPDATE bookings SET status = 'completed', completed_at = ?, updated_at = ? WHERE id = ?
            """, (now, now, booking_id))
            cursor.execute("""
                UPDATE trips SET end_time = ?, status = 'completed'
                WHERE booking_id = ? AND driver_id = ?
            """, (now, booking_id, user_id))
        else:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        try:
            client_ip = req.client.host if req and req.client else None
        except:
            client_ip = None
        log_audit(conn, user_id, "status_update", "booking", booking_id, old_status, status, client_ip)
        conn.commit()
        return {"success": True, "status": status}

@app.post("/api/driver/location")
async def submit_driver_location(data: LocationData, user_id: int = Depends(require_role("driver"))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM trips WHERE driver_id = ? AND status = 'ongoing'
            ORDER BY start_time DESC LIMIT 1
        """, (user_id,))
        trip = cursor.fetchone()
        if not trip:
            raise HTTPException(status_code=400, detail="No active trip")

        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO location_history (trip_id, driver_id, latitude, longitude, speed, heading, accuracy, altitude, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (trip["id"], user_id, data.latitude, data.longitude, data.speed, data.heading, data.accuracy, data.altitude, now))
        conn.commit()

        try:
            await manager.broadcast({
                "type": "location_update",
                "driver_id": user_id,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "speed": data.speed,
                "timestamp": now
            })
        except Exception:
            pass

        return {"success": True}

@app.get("/api/driver/current-location/{driver_id}")
async def get_driver_location(driver_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM location_history
            WHERE driver_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (driver_id,))
        location = cursor.fetchone()
        if not location:
            raise HTTPException(status_code=404, detail="No location data")
        return dict(location)

# ==================== WEBSOCKET ====================
@app.websocket("/ws/tracking")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==================== SERVE FRONTEND ====================
@app.get("/")
async def serve_index():
    index_path = os.path.join(PROJECT_ROOT, "frontend", "login.html")
    if not os.path.isfile(index_path):
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)

@app.get("/pengguna.html")
async def serve_pengguna():
    file_path = os.path.join(PROJECT_ROOT, "frontend", "pengguna.html")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/admin.html")
async def serve_admin():
    file_path = os.path.join(PROJECT_ROOT, "frontend", "admin.html")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/driver.html")
async def serve_driver():
    file_path = os.path.join(PROJECT_ROOT, "frontend", "driver.html")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

@app.get("/config")
def get_config():
    host = os.environ.get("UISI_HOST", "127.0.0.1")
    port = int(os.environ.get("UISI_PORT", "8000"))
    return {"HOST": host, "PORT": port}

# ==================== RUN SERVER ====================
# ==================== RUN SERVER (MODIFIED - TAMBAHKAN DI AKHIR main.py) ====================

if len(sys.argv) < 3:
    print("Usage: python main.py [HOST] [PORT]")
    print("Example: python main.py 0.0.0.0 8000")
    sys.exit(1)

HOST = sys.argv[1]
PORT = int(sys.argv[2])

if __name__ == "__main__":
    import uvicorn
    import asyncio
    
    print("""
╔═══════════════════════════════════════════════╗
║                                               ║
║            SHUTTLE CAR UISI v0.9.0            ║
║                                               ║
╚═══════════════════════════════════════════════╝
""")
    
    # Check if SSL certificates exist
    ssl_keyfile = "key.pem"
    ssl_certfile = "cert.pem"
    use_ssl = os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile)
    
    if use_ssl:
        print(f"""
🔒 SSL/HTTPS Mode ENABLED
   📡 Host: {HOST}
   🔌 Port: {PORT}
   📚 API Docs: https://{HOST}:{PORT}/docs
   🌍 Frontend: https://{HOST}:{PORT}/
   🚗 Driver: https://{HOST}:{PORT}/driver.html
""")
    else:
        print(f"""
⚠️  Running in HTTP mode (SSL certificates not found)
   📡 Host: {HOST}
   🔌 Port: {PORT}
   📚 API Docs: http://{HOST}:{PORT}/docs
   🌍 Frontend: http://{HOST}:{PORT}/

💡 GPS Tracking hanya jalan di:
   ✅ http://localhost:{PORT} (local testing)
   ❌ http://{HOST}:{PORT} (akan di-block browser)
""")
    
    print("""
🔑 Default Accounts:
   Admin  : admin@uisi.ac.id / admin123
   Driver : driver1@uisi.ac.id / driver123
   Student: [email]@student.uisi.ac.id (auto-register)

Press CTRL+C to stop server
════════════════════════════════════════════════════════════════════
""")
    
    async def main():
        config_params = {
            "app": "main:app",
            "host": HOST,
            "port": PORT,
            "reload": True,
            "log_level": "info"
        }
        
        # Add SSL if certificates exist
        if use_ssl:
            config_params["ssl_keyfile"] = ssl_keyfile
            config_params["ssl_certfile"] = ssl_certfile
        
        config = uvicorn.Config(**config_params)
        server = uvicorn.Server(config)
        await server.serve()
    
    asyncio.run(main())
