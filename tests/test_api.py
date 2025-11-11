"""
Test API Endpoints
==================

INSTRUKSI:
Script untuk test semua API endpoints.

SEBELUM JALANKAN:
1. Pastikan backend sudah jalan: python main.py
2. Database sudah di-setup

CARA JALANKAN:
python test_api.py

CATATAN:
- Script ini akan test semua endpoint
- Akan create sample data
- Safe untuk testing (tidak merusak data production)
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def print_header(text):
    """Print header untuk setiap test"""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def test_connection():
    """Test 1: Connection ke server"""
    print_header("TEST 1: Server Connection")
    try:
        response = requests.get(f"{BASE_URL}/api", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
            data = response.json()
            print(f"   API Version: {data.get('version', 'N/A')}")
            return True
        else:
            print(f"⚠️  Server responded with status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server!")
        print("   Make sure backend is running: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_get_locations():
    """Test 2: Get all locations"""
    print_header("TEST 2: Get All Locations")
    try:
        response = requests.get(f"{BASE_URL}/api/locations")
        locations = response.json()
        print(f"✅ Found {len(locations)} locations:")
        for i, loc in enumerate(locations[:5], 1):  # Show first 5
            name = loc['location_name'].split(" - ")[0]
            print(f"   {i}. {name}")
            print(f"      GPS: ({loc['latitude']}, {loc['longitude']})")
        if len(locations) > 5:
            print(f"   ... and {len(locations)-5} more")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_create_route_request():
    """Test 3: Create route request"""
    print_header("TEST 3: Create Route Request")
    try:
        data = {
            "from_location": "Pos P13",
            "to_location": "Ged 1 A",
            "requested_by": "Test Script",
            "note": "Automated test request"
        }
        response = requests.post(f"{BASE_URL}/api/route/request", json=data)
        result = response.json()
        
        if result.get('success'):
            print("✅ Route request created!")
            print(f"   Request ID: {result.get('request_id')}")
            print(f"   From: {data['from_location']}")
            print(f"   To: {data['to_location']}")
            return result.get('request_id')
        else:
            print("⚠️  Request failed")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_get_requests():
    """Test 4: Get pending requests"""
    print_header("TEST 4: Get Pending Requests")
    try:
        response = requests.get(f"{BASE_URL}/api/route/requests?status=pending")
        requests_list = response.json()
        print(f"✅ Found {len(requests_list)} pending request(s):")
        for req in requests_list[:3]:
            print(f"   ID {req['id']}: {req['from_location']} → {req['to_location']}")
            print(f"   Requested by: {req['requested_by']}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_full_workflow():
    """Test 5: Full workflow simulation"""
    print_header("TEST 5: Full Workflow Simulation")
    
    try:
        # 1. Create request
        print("\n1️⃣  Creating route request...")
        request_data = {
            "from_location": "Pos P13",
            "to_location": "Ged 1 B",
            "requested_by": "Workflow Test"
        }
        response = requests.post(f"{BASE_URL}/api/route/request", json=request_data)
        request_id = response.json().get('request_id')
        print(f"   ✅ Request created: ID {request_id}")
        
        # 2. Start trip
        print("\n2️⃣  Starting trip...")
        requests.post(f"{BASE_URL}/api/trip/start")
        print("   ✅ Trip started")
        
        # 3. Send location (simulate movement)
        print("\n3️⃣  Sending GPS locations...")
        locations = [
            (-7.1633, 112.6280, "Pos P13"),
            (-7.1640, 112.6285, "Moving..."),
            (-7.1655, 112.6290, "Ged 1 B"),
        ]
        
        for lat, lng, desc in locations:
            loc_data = {
                "latitude": lat,
                "longitude": lng,
                "speed": 25.0,
                "heading": 90.0,
                "accuracy": 8.0
            }
            response = requests.post(f"{BASE_URL}/api/location", json=loc_data)
            result = response.json()
            print(f"   📍 {desc}: {result.get('message')}")
            time.sleep(1)
        
        # 4. Get current location
        print("\n4️⃣  Getting current location...")
        response = requests.get(f"{BASE_URL}/api/shuttle/current")
        current = response.json()
        print(f"   ✅ Current position: ({current['latitude']}, {current['longitude']})")
        print(f"   Speed: {current['speed']} km/h")
        
        # 5. Get distance stats
        print("\n5️⃣  Getting distance statistics...")
        response = requests.get(f"{BASE_URL}/api/shuttle/distance")
        stats = response.json()
        print(f"   ✅ Current trip: {stats['current_trip_distance']} km")
        print(f"   Today total: {stats['today_distance']} km")
        
        # 6. End trip
        print("\n6️⃣  Ending trip...")
        requests.post(f"{BASE_URL}/api/trip/end")
        print("   ✅ Trip ended")
        
        print("\n✅ WORKFLOW TEST COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"\n❌ Workflow test failed: {e}")
        return False

def run_all_tests():
    """Run semua tests"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       🧪 UISI SHUTTLE API - TEST SUITE 🧪                 ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
""")
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Connection
    if test_connection():
        tests_passed += 1
    else:
        tests_failed += 1
        print("\n❌ Cannot continue - server not running")
        return
    
    # Test 2: Get locations
    if test_get_locations():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 3: Create request
    request_id = test_create_route_request()
    if request_id:
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 4: Get requests
    if test_get_requests():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Test 5: Full workflow
    if test_full_workflow():
        tests_passed += 1
    else:
        tests_failed += 1
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Tests passed: {tests_passed}")
    print(f"❌ Tests failed: {tests_failed}")
    print(f"📊 Success rate: {(tests_passed/(tests_passed+tests_failed)*100):.1f}%")
    print("="*60)
    
    if tests_failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️  Some tests failed. Check errors above.")

if __name__ == "__main__":
    run_all_tests()