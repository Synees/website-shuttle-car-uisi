const API_URL = window.location.origin;
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

let isTracking = false;
let watchId;

// Check auth
if (!token || user.role !== 'driver') {
	window.location.href = '/';
}

document.getElementById('driver-name').textContent = user.name;

function showAlert(message) {
	const alert = document.getElementById('alert');
	alert.textContent = message;
	alert.style.display = 'block';
	setTimeout(() => alert.style.display = 'none', 5000);
}

function logout() {
	if (isTracking) {
		alert('Matikan GPS tracking dulu!');
		return;
	}
	localStorage.clear();
	window.location.href = '/';
}

// ==================== VIEW SCHEDULE ====================

async function viewSchedule() {
	try {
		// Check if schedule exists
		const statusResponse = await fetch(`${API_URL}/api/schedule/status`);
		const statusData = await statusResponse.json();
		
		if (!statusData.exists) {
			showAlert('❌ Jadwal belum diupload oleh admin. Silakan hubungi admin untuk mengunggah jadwal.');
			return;
		}
		
		// Open schedule in new tab
		window.open(`${API_URL}/api/schedule`, '_blank');
	} catch (error) {
		console.error('Error viewing schedule:', error);
		showAlert('❌ Gagal membuka jadwal. Jadwal mungkin belum tersedia.');
	}
}

// ==================== MAP INITIALIZATION ====================

// Initialize map for driver (if map element exists)
function setupDriverMap() {
	const mapElement = document.getElementById('map');
	if (!mapElement) return; // Map not available in this view
	
	// Initialize map
	initMap(-7.1645, 112.6285, 16);
	
	// Load locations on map
	loadDriverLocations();
}

// Load locations for driver view
async function loadDriverLocations() {
	try {
		const response = await fetch(`${API_URL}/api/locations`);
		const locations = await response.json();
		
		// Display on map without select options
		loadLocationsOnMap(locations, false);
		
	} catch (error) {
		console.error('Error loading locations:', error);
	}
}

// ==================== GPS TRACKING ====================

// Toggle GPS Tracking
function toggleTracking() {
	if (!isTracking) {
		startTracking();
	} else {
		stopTracking();
	}
}

function startTracking() {
	if (!navigator.geolocation) {
		showAlert('GPS tidak didukung browser Anda');
		return;
	}

	const btn = document.getElementById('tracking-btn');
	btn.className = 'tracking-button stop';
	btn.innerHTML = '<i class="fas fa-stop"></i><span>STOP</span>';
	
	document.getElementById('gps-status').className = 'status active';
	document.getElementById('gps-status').textContent = 'GPS Aktif - Mengirim Lokasi...';
	
	isTracking = true;

	// Watch position
	watchId = navigator.geolocation.watchPosition(
		sendLocation,
		handleGPSError,
		{
			enableHighAccuracy: true,
			maximumAge: 0,
			timeout: 5000
		}
	);
}

function stopTracking() {
	if (watchId) {
		navigator.geolocation.clearWatch(watchId);
	}

	const btn = document.getElementById('tracking-btn');
	btn.className = 'tracking-button start';
	btn.innerHTML = '<i class="fas fa-location-arrow"></i><span>START</span>';
	
	document.getElementById('gps-status').className = 'status inactive';
	document.getElementById('gps-status').textContent = 'GPS Tidak Aktif';
	
	isTracking = false;
}

async function sendLocation(position) {
	const coords = position.coords;
	
	// Update UI
	const speedKmh = (coords.speed || 0) * 3.6; // m/s to km/h
	document.getElementById('speed').textContent = Math.round(speedKmh);
	document.getElementById('accuracy').textContent = Math.round(coords.accuracy);

	try {
		await fetch(`${API_URL}/api/driver/location`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'Authorization': `Bearer ${token}`
			},
			body: JSON.stringify({
				latitude: coords.latitude,
				longitude: coords.longitude,
				speed: speedKmh,
				heading: coords.heading || 0,
				accuracy: coords.accuracy
			})
		});
		
		// Update driver marker on map if map exists
		const mapElement = document.getElementById('map');
		if (mapElement && typeof updateDriverMarker === 'function') {
			updateDriverMarker(user.id, {
				latitude: coords.latitude,
				longitude: coords.longitude,
				speed: speedKmh,
				heading: coords.heading || 0,
				timestamp: new Date().toISOString()
			});
		}
	} catch (error) {
		console.error('Error sending location:', error);
	}
}

function handleGPSError(error) {
	let message = 'GPS Error: ';
	switch(error.code) {
		case error.PERMISSION_DENIED:
			message += 'Izinkan akses lokasi di browser';
			break;
		case error.POSITION_UNAVAILABLE:
			message += 'Lokasi tidak tersedia';
			break;
		case error.TIMEOUT:
			message += 'Request timeout';
			break;
	}
	showAlert(message);
}

// ==================== BOOKING MANAGEMENT ====================

// Load my bookings
async function loadMyBookings() {
	try {
		const response = await fetch(`${API_URL}/api/driver/bookings`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		const bookings = await response.json();
		
		const list = document.getElementById('booking-list');
		
		if (bookings.length === 0) {
			list.innerHTML = `
				<div class="empty-state">
					<i class="fas fa-inbox"></i>
					<p>Belum ada booking</p>
				</div>
			`;
			return;
		}
		
		list.innerHTML = bookings.map(b => `
			<div class="booking-item">
				<div class="booking-header">
					<span class="booking-id">#${b.id}</span>
					<span class="status-badge">${getStatusText(b.status)}</span>
				</div>
				<div class="booking-route">
					<strong>${b.from_location}</strong>
					<i class="fas fa-arrow-right"></i>
					<strong>${b.to_location}</strong>
				</div>
				<div class="booking-user">
					<i class="fas fa-user"></i> ${b.user_name}
					${b.user_phone ? `<br><i class="fas fa-phone"></i> ${b.user_phone}` : ''}
				</div>
				${getBookingActions(b)}
			</div>
		`).join('');
	} catch (error) {
		showAlert('Gagal memuat booking');
	}
}

function getStatusText(status) {
	const map = {
		'accepted': 'Diterima',
		'driver_arriving': 'Dalam Perjalanan ke Lokasi Jemput',
		'ongoing': 'Sedang Berjalan',
		'completed': 'Selesai'
	};
	return map[status] || status;
}

function getBookingActions(booking) {
	if (booking.status === 'accepted') {
		return `<button class="btn btn-arriving" onclick="updateStatus(${booking.id}, 'driver_arriving')">
			<i class="fas fa-car"></i> Tiba di Lokasi Jemput
		</button>`;
	} else if (booking.status === 'driver_arriving') {
		return `<button class="btn btn-start" onclick="updateStatus(${booking.id}, 'ongoing')">
			<i class="fas fa-play"></i> Mulai Perjalanan
		</button>`;
	} else if (booking.status === 'ongoing') {
		return `<button class="btn btn-complete" onclick="updateStatus(${booking.id}, 'completed')">
			<i class="fas fa-check"></i> Selesai
		</button>`;
	}
	return '';
}

async function updateStatus(bookingId, status) {
	if (status === 'ongoing' && !isTracking) {
		alert('Aktifkan GPS tracking dulu!');
		return;
	}

	try {
		const response = await fetch(`${API_URL}/api/driver/bookings/${bookingId}/status`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				'Authorization': `Bearer ${token}`
			},
			body: JSON.stringify({status})
		});
		
		const data = await response.json();
		
		if (response.ok && data.success) {
			loadMyBookings();
		} else {
			showAlert('Gagal update status');
		}
	} catch (error) {
		showAlert('Koneksi gagal');
	}
}

// ==================== INITIALIZATION ====================

// Initialize
setupDriverMap(); // Setup map if available
loadMyBookings();

// Refresh bookings every 15 seconds
setInterval(loadMyBookings, 15000);
