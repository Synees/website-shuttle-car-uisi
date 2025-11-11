"""
UISI Shuttle Tracking - Main Backend
=====================================

INSTRUKSI MENJALANKAN:
1. Pastikan sudah install dependencies: pip install -r requirements.txt
2. Setup database dulu: python setup_database.py
3. Jalankan server: python main.py
4. Buka browser: http://localhost:8000/docs

CATATAN PENTING:
- Server ini untuk LOCALHOST development
- Untuk production, gunakan Gunicorn (lihat docs/DEPLOYMENT.md)
- Koordinat GPS perlu di-verify dulu! (lihat scripts/update_coordinates.py)

FITUR UTAMA:
- Real-time GPS tracking
- Flexible route requests (sesuai permintaan mahasiswa via WA)
- Distance & ETA calculation
- WebSocket untuk real-time updates
- Support 8 lokasi kampus UISI

ENDPOINTS:
- POST /api/location - Submit GPS dari driver
- GET /api/shuttle/current - Posisi shuttle saat ini
- POST /api/route/request - Request rute baru
- GET /api/route/requests - Lihat semua request
- POST /api/route/accept/{id} - Accept request
- GET /api/route/active - Rute yang sedang aktif
- Dan masih banyak lagi (lihat /docs untuk lengkapnya)

Author: [Your Name]
Date: November 2025
Version: 2.0.0
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import sqlite3
import json
import math
from contextlib import contextmanager
import os
import sys

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATABASE = os.path.join(PROJECT_ROOT, 'backend', 'shuttle.db')

# ==================== MODELS ====================

class LocationData(BaseModel):
    """Model untuk data GPS dari driver"""
    shuttle_id: int = 1
    latitude: float
    longitude: float
    speed: float = 0.0
    heading: float = 0.0
    accuracy: float = 10.0
    timestamp: Optional[str] = None

class RouteRequest(BaseModel):
    """Model untuk request rute dari mahasiswa via WA"""
    from_location: str
    to_location: str
    requested_by: Optional[str] = "Mahasiswa"
    request_time: Optional[str] = None
    note: Optional[str] = None

# ==================== DATABASE ====================

DATABASE = "shuttle.db"

@contextmanager
def get_db():
    """Context manager untuk database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ==================== UTILITY FUNCTIONS ====================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Hitung jarak antara 2 koordinat menggunakan Haversine formula
    Returns: jarak dalam kilometer
    """
    R = 6371  # Radius bumi dalam km
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def find_location_coords(location_name: str) -> tuple:
    """Cari koordinat lokasi berdasarkan nama"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT latitude, longitude FROM routes 
            WHERE location_name LIKE ? 
            LIMIT 1
        """, (f"%{location_name}%",))
        
        result = cursor.fetchone()
        if result:
            return (result['latitude'], result['longitude'])
        return None

def calculate_eta(current_lat: float, current_lon: float, 
                  dest_lat: float, dest_lon: float, 
                  avg_speed: float) -> int:
    """Hitung ETA dalam menit"""
    distance = haversine_distance(current_lat, current_lon, dest_lat, dest_lon)
    if avg_speed <= 0:
        avg_speed = 25  # Default speed untuk shuttle kampus
    eta_hours = distance / avg_speed
    eta_minutes = int(eta_hours * 60)
    return eta_minutes

def get_average_speed(shuttle_id: int = 1, minutes: int = 5) -> float:
    """Get average speed dalam N menit terakhir"""
    with get_db() as conn:
        cursor = conn.cursor()
        time_threshold = (datetime.now() - timedelta(minutes=minutes)).isoformat()
        cursor.execute("""
            SELECT AVG(speed) as avg_speed 
            FROM location_history 
            WHERE shuttle_id = ? AND timestamp > ? AND speed > 0
        """, (shuttle_id, time_threshold))
        result = cursor.fetchone()
        return result['avg_speed'] if result['avg_speed'] else 25.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Check database saat startup"""
    if not os.path.exists(DATABASE):
        print("⚠️  WARNING: Database not found!")
        print("   Run: python setup_database.py")
    else:
        print("✅ Database found")
    print("🚀 Server started...")
    print("🚀 UISI Shuttle Tracking Server started")
    print("📍 API Docs: http://localhost:8000/docs")
    print("🌐 Frontend: http://localhost:8000/")
    yield
    print("👋 Server shutting down...")

# ==================== FASTAPI APP ====================

app = FastAPI(
    title="UISI Shuttle Tracking API",
    description="Sistem tracking shuttle kampus dengan flexible routing",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - allow all origins untuk development
# CATATAN: Untuk production, ganti "*" dengan domain spesifik
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
if os.path.exists("../frontend"):
    app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# WebSocket manager untuk real-time updates
class ConnectionManager:
    """Manage WebSocket connections untuk broadcast real-time"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message ke semua connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                print(f"❌ Broadcast error: {e}")
                dead_connections.append(connection)
        
        # Remove dead connections
        for conn in dead_connections:
            self.active_connections.remove(conn)

manager = ConnectionManager()

# ==================== ENDPOINTS ====================

@app.get("/")
async def serve_frontend():
    """Serve halaman mahasiswa (tracking)"""
    frontend_path = "../frontend/index.html"
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {
        "message": "UISI Shuttle Tracking API",
        "docs": "/docs",
        "frontend": "Frontend belum di-setup. Lihat folder frontend/"
    }

@app.get("/driver.html")
async def serve_driver():
    """Serve halaman driver"""
    driver_path = "../frontend/driver.html"
    if os.path.exists(driver_path):
        return FileResponse(driver_path)
    return {"error": "Driver page not found"}

@app.get("/admin.html")
async def serve_admin():
    """Serve halaman admin"""
    admin_path = "../frontend/admin.html"
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return {"error": "Admin page not found"}

@app.get("/api")
async def api_info():
    """API Information"""
    return {
        "name": "UISI Shuttle Tracking API",
        "version": "2.0.0",
        "university": "Universitas Internasional Semen Indonesia",
        "endpoints": {
            "tracking": {
                "POST /api/location": "Submit GPS location",
                "GET /api/shuttle/current": "Get current location",
                "GET /api/shuttle/distance": "Get distance stats"
            },
            "routing": {
                "POST /api/route/request": "Create route request",
                "GET /api/route/requests": "Get all requests",
                "POST /api/route/accept/{id}": "Accept request",
                "GET /api/route/active": "Get active route",
                "POST /api/route/complete": "Complete route"
            },
            "trip": {
                "POST /api/trip/start": "Start trip",
                "POST /api/trip/end": "End trip"
            },
            "locations": {
                "GET /api/locations": "Get all locations"
            },
            "websocket": {
                "WS /ws/tracking": "WebSocket for real-time updates"
            }
        },
        "docs": "/docs"
    }

@app.post("/api/location")
async def submit_location(data: LocationData):
    """
    Submit GPS location dari driver
    
    CARA PAKAI:
    - Driver HP kirim GPS data setiap 5 detik
    - Data disimpan ke database
    - Broadcast ke semua client via WebSocket
    - Hitung jarak increment otomatis
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get last location untuk hitung jarak
            cursor.execute("""
                SELECT latitude, longitude FROM location_history 
                WHERE shuttle_id = ? 
                ORDER BY timestamp DESC LIMIT 1
            """, (data.shuttle_id,))
            
            last_location = cursor.fetchone()
            distance_increment = 0.0
            
            if last_location:
                distance_increment = haversine_distance(
                    last_location['latitude'], 
                    last_location['longitude'],
                    data.latitude, 
                    data.longitude
                )
            
            # Insert new location
            timestamp = data.timestamp if data.timestamp else datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO location_history 
                (shuttle_id, latitude, longitude, speed, heading, accuracy, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data.shuttle_id, data.latitude, data.longitude, 
                  data.speed, data.heading, data.accuracy, timestamp))
            
            # Update shuttle status
            cursor.execute("""
                UPDATE shuttles 
                SET status = 'active', 
                    total_distance = total_distance + ?
                WHERE id = ?
            """, (distance_increment, data.shuttle_id))
            
            # Update trip distance
            cursor.execute("""
                UPDATE trips 
                SET distance = distance + ?
                WHERE shuttle_id = ? AND status = 'ongoing'
            """, (distance_increment, data.shuttle_id))
            
            conn.commit()
        
        # Broadcast ke semua client
        await manager.broadcast({
            "type": "location_update",
            "data": {
                "shuttle_id": data.shuttle_id,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "speed": data.speed,
                "heading": data.heading,
                "timestamp": timestamp
            }
        })
        
        return {
            "success": True,
            "message": "Location updated",
            "distance_increment": round(distance_increment, 3)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/route/request")
async def create_route_request(request: RouteRequest):
    """
    Create route request (dari WhatsApp atau mahasiswa)
    
    CARA PAKAI:
    - Admin input request dari grup WA
    - Atau mahasiswa request via form
    - Driver akan lihat di dashboard
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            request_time = request.request_time if request.request_time else datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO route_requests 
                (from_location, to_location, requested_by, request_time, status, note)
                VALUES (?, ?, ?, ?, 'pending', ?)
            """, (request.from_location, request.to_location, 
                  request.requested_by, request_time, request.note))
            
            request_id = cursor.lastrowid
            conn.commit()
        
        # Broadcast ke driver
        await manager.broadcast({
            "type": "new_route_request",
            "data": {
                "id": request_id,
                "from": request.from_location,
                "to": request.to_location,
                "requested_by": request.requested_by,
                "time": request_time
            }
        })
        
        return {
            "success": True,
            "message": "Route request created",
            "request_id": request_id
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/route/requests")
async def get_route_requests(status: str = "pending", limit: int = 20):
    """
    Get route requests
    
    Parameters:
    - status: pending, accepted, completed, all
    - limit: max records
    """
    with get_db() as conn:
        cursor = conn.cursor()
        
        if status == "all":
            cursor.execute("""
                SELECT * FROM route_requests 
                ORDER BY request_time DESC 
                LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT * FROM route_requests 
                WHERE status = ?
                ORDER BY request_time DESC 
                LIMIT ?
            """, (status, limit))
        
        requests = cursor.fetchall()
        return [dict(row) for row in requests]

@app.post("/api/route/accept/{request_id}")
async def accept_route_request(request_id: int):
    """
    Driver accept route request
    
    CARA PAKAI:
    - Driver lihat pending requests
    - Klik accept
    - Route otomatis jadi active
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Get request details
            cursor.execute("""
                SELECT * FROM route_requests WHERE id = ?
            """, (request_id,))
            request = cursor.fetchone()
            
            if not request:
                raise HTTPException(status_code=404, detail="Request not found")
            
            # Update request status
            # cursor.execute("""
            #     UPDATE route_requests
            #     SET status = 'accepted'
            #     WHERE id = ?
            # """, (request_id,))
            cursor.execute("BEGIN IMMEDIATE")  # Lock database
            cursor.execute("SELECT status FROM route_requests WHERE id = ?",
                           (request_id,))
            current_status = cursor.fetchone()

            if current_status['status'] != 'pending':
                raise HTTPException(400, "Request already accepted")
            
            # Clear old active routes
            cursor.execute("""
                UPDATE active_routes 
                SET status = 'completed'
                WHERE shuttle_id = 1 AND status = 'active'
            """)
            
            # Set as active route
            cursor.execute("""
                INSERT INTO active_routes (from_location, to_location, started_at)
                VALUES (?, ?, ?)
            """, (request['from_location'], request['to_location'], 
                  datetime.now().isoformat()))
            
            conn.commit()
        
        return {
            "success": True,
            "message": "Route accepted and set as active",
            "from": request['from_location'],
            "to": request['to_location']
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/route/active")
async def get_active_route(shuttle_id: int = 1):
    """Get current active route dengan ETA"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM active_routes 
            WHERE shuttle_id = ? AND status = 'active'
            ORDER BY started_at DESC 
            LIMIT 1
        """, (shuttle_id,))
        
        route = cursor.fetchone()
        if not route:
            return {"active": False, "message": "No active route"}
        
        # Get current location
        cursor.execute("""
            SELECT latitude, longitude FROM location_history
            WHERE shuttle_id = ?
            ORDER BY timestamp DESC LIMIT 1
        """, (shuttle_id,))
        
        current = cursor.fetchone()
        
        # Calculate ETA
        if current:
            dest_coords = find_location_coords(route['to_location'])
            if dest_coords:
                avg_speed = get_average_speed(shuttle_id)
                eta = calculate_eta(
                    current['latitude'], current['longitude'],
                    dest_coords[0], dest_coords[1],
                    avg_speed
                )
                
                return {
                    "active": True,
                    "from": route['from_location'],
                    "to": route['to_location'],
                    "started_at": route['started_at'],
                    "eta_minutes": eta,
                    "current_location": {
                        "lat": current['latitude'],
                        "lng": current['longitude']
                    }
                }
        
        return {
            "active": True,
            "from": route['from_location'],
            "to": route['to_location'],
            "started_at": route['started_at']
        }

@app.post("/api/route/complete")
async def complete_active_route(shuttle_id: int = 1):
    """Mark active route sebagai completed"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE active_routes 
                SET status = 'completed'
                WHERE shuttle_id = ? AND status = 'active'
            """, (shuttle_id,))
            
            # Update corresponding request
            cursor.execute("""
                UPDATE route_requests
                SET status = 'completed'
                WHERE status = 'accepted'
                LIMIT 1
            """)
            
            conn.commit()
        
        return {"success": True, "message": "Route completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/locations")
async def get_all_locations():
    """Get semua lokasi kampus UISI"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT location_name, latitude, longitude 
            FROM routes 
            ORDER BY point_order
        """)
        locations = cursor.fetchall()
        return [dict(row) for row in locations]

@app.get("/api/shuttle/current")
async def get_current_location(shuttle_id: int = 1):
    """Get current shuttle location"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM location_history 
            WHERE shuttle_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        """, (shuttle_id,))
        location = cursor.fetchone()
        if not location:
            raise HTTPException(status_code=404, detail="No location data")
        return dict(location)

@app.get("/api/shuttle/distance")
async def get_distance(shuttle_id: int = 1):
    """Get distance statistics"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Today's distance
        today = datetime.now().date().isoformat()
        cursor.execute("""
            SELECT SUM(distance) as total 
            FROM trips 
            WHERE shuttle_id = ? AND DATE(start_time) = ?
        """, (shuttle_id, today))
        today_result = cursor.fetchone()
        today_distance = today_result['total'] if today_result['total'] else 0.0
        
        # Current trip
        cursor.execute("""
            SELECT distance FROM trips 
            WHERE shuttle_id = ? AND status = 'ongoing'
            ORDER BY start_time DESC LIMIT 1
        """, (shuttle_id,))
        trip_result = cursor.fetchone()
        trip_distance = trip_result['distance'] if trip_result else 0.0
        
        # Total distance
        cursor.execute("""
            SELECT total_distance FROM shuttles WHERE id = ?
        """, (shuttle_id,))
        total_result = cursor.fetchone()
        total_distance = total_result['total_distance'] if total_result else 0.0
    
    return {
        "today_distance": round(today_distance, 2),
        "current_trip_distance": round(trip_distance, 2),
        "total_distance": round(total_distance, 2)
    }

@app.post("/api/trip/start")
async def start_trip(shuttle_id: int = 1):
    """Start new trip"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trips (shuttle_id, start_time, status)
                VALUES (?, ?, 'ongoing')
            """, (shuttle_id, datetime.now().isoformat()))
            conn.commit()
        return {"success": True, "message": "Trip started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trip/end")
async def end_trip(shuttle_id: int = 1):
    """End current trip"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trips 
                SET end_time = ?, status = 'completed'
                WHERE shuttle_id = ? AND status = 'ongoing'
            """, (datetime.now().isoformat(), shuttle_id))
            
            cursor.execute("""
                UPDATE shuttles SET status = 'inactive' WHERE id = ?
            """, (shuttle_id,))
            conn.commit()
        return {"success": True, "message": "Trip ended"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/tracking")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket untuk real-time updates
    
    CARA PAKAI:
    - Frontend connect ke ws://localhost:8000/ws/tracking
    - Akan terima update setiap ada location/request baru
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back (optional)
            # await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       🚌 UISI SHUTTLE TRACKING SYSTEM 🚌                  ║
║                                                            ║
║   Universitas Internasional Semen Indonesia                ║
║   Gresik, Jawa Timur                                       ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝

STARTING SERVER...

📍 API Documentation: http://localhost:8000/docs
🌐 Frontend (Mahasiswa): http://localhost:8000/
🚗 Driver Interface: http://localhost:8000/driver.html
🛠️  Admin Panel: http://localhost:8000/admin.html

CATATAN PENTING:
⚠️  Koordinat GPS masih ESTIMASI - perlu di-update!
    Jalankan: cd scripts && python update_coordinates.py

💡 Untuk akses dari HP driver:
    1. Cari IP komputer: ipconfig (Windows) / ifconfig (Mac/Linux)
    2. Buka di HP: http://[IP]:8000/driver.html
    
Press CTRL+C to stop server
════════════════════════════════════════════════════════════
""")
    
    # Check database
    if not os.path.exists(DATABASE):
        print("⚠️  DATABASE NOT FOUND!")
        print("   Please run: python setup_database.py")
        print("   Exiting...")
        exit(1)
    
    # Run server
    uvicorn.run(
        app, 
        host="0.0.0.0",  # Allow access dari network
        port=8000, 
        reload=True,  # Auto-reload saat code berubah
        log_level="info"
    )
