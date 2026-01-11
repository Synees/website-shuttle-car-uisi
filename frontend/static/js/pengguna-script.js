const API_URL = window.location.origin;
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

let ws = null;
// ✅ PERUBAHAN: Tambah variable untuk tracking driver polling
let driverTrackingInterval = null;
let activeDriverIds = new Set(); // Set untuk menyimpan ID driver yang sedang aktif

// Check auth
if (!token || user.role !== 'pengguna') {
	window.location.href = '/';
}

// Display user info
document.getElementById('user-name').textContent = user.name;
document.getElementById('user-email').textContent = user.email;

function showAlert(message, type = 'error') {
	const alert = document.getElementById('alert');
	alert.textContent = message;
	alert.className = `alert alert-${type} show`;
	setTimeout(() => alert.classList.remove('show'), 5000);
}

function logout() {
	if (ws) ws.close();
	// ✅ PERUBAHAN: Clear interval saat logout
	if (driverTrackingInterval) {
		clearInterval(driverTrackingInterval);
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
			showAlert('❌ Jadwal belum diupload oleh admin. Silakan hubungi admin untuk mengunggah jadwal.', 'error');
			return;
		}
		
		// Open schedule in new tab
		window.open(`${API_URL}/api/schedule`, '_blank');
	} catch (error) {
		console.error('Error viewing schedule:', error);
		showAlert('❌ Gagal membuka jadwal. Jadwal mungkin belum tersedia.', 'error');
	}
}

// ==================== MAP INITIALIZATION ====================
// Initialize map with location button
function setupMap() {
	// Initialize map
	initMap(-7.1645, 112.6285, 16);
	
	// Add location button
	createLocationButton(() => {
		getUserLocation(
			(location) => {
				showAlert('📍 Lokasi Anda berhasil dideteksi', 'success');
			},
			(error) => {
				handleGeolocationError(error);
			}
		);
	});
	
	// Try to get user's current location on init
	getUserLocation(
		(location) => {
			showAlert('📍 Lokasi Anda berhasil dideteksi', 'success');
		},
		(error) => {
			handleGeolocationError(error);
		}
	);
}

// Handle geolocation errors
function handleGeolocationError(error) {
	let message = '';
	
	switch(error.code) {
		case error.PERMISSION_DENIED:
			message = '❌ Akses lokasi ditolak. Mohon izinkan akses lokasi di browser Anda.';
			break;
		case error.POSITION_UNAVAILABLE:
			message = '⚠️ Informasi lokasi tidak tersedia.';
			break;
		case error.TIMEOUT:
			message = '⏱️ Request lokasi timeout. Coba lagi.';
			break;
		default:
			message = '❌ Gagal mendapatkan lokasi.';
	}
	
	showAlert(message, 'error');
}

// ==================== LOCATIONS ====================

// Load locations from API and display on map
async function loadLocations() {
	try {
		const response = await fetch(`${API_URL}/api/locations`);
		const locations = await response.json();
		
		// Display on map with select options
		loadLocationsOnMap(locations, true, 'from-location', 'to-location');
		
		// Auto-select nearest location if user location is available
		const currentLocation = getCurrentUserLocation();
		if (currentLocation) {
			const nearest = autoSelectNearestLocation(locations, 'from-location');
			if (nearest) {
				showAlert(`📍 Lokasi terdekat: ${nearest.location.name} (${Math.round(nearest.distance * 1000)}m)`, 'info');
			}
		}
		
	} catch (error) {
		showAlert('Gagal memuat lokasi', 'error');
	}
}

// ==================== BOOKINGS ====================

// Create booking
async function createBooking(event) {
	event.preventDefault();
	
	const fromId = parseInt(document.getElementById('from-location').value);
	const toId = parseInt(document.getElementById('to-location').value);
	const notes = document.getElementById('notes').value;
	
	if (fromId === toId) {
		showAlert('Lokasi penjemputan dan tujuan tidak boleh sama', 'error');
		return;
	}
	
	const btn = document.getElementById('btn-booking');
	btn.disabled = true;
	btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
	
	try {
		const response = await fetch(`${API_URL}/api/bookings`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'Authorization': `Bearer ${token}`
			},
			body: JSON.stringify({
				from_location_id: fromId,
				to_location_id: toId,
				notes: notes || null,
				passenger_count: 1
			})
		});
		
		const data = await response.json();
		
		if (response.ok && data.success) {
			showAlert('✅ Booking berhasil dibuat! Driver akan segera mengonfirmasi.', 'success');
			document.getElementById('notes').value = '';
			loadMyBookings();
			
			// Scroll to bookings section
			document.getElementById('booking-list').scrollIntoView({ behavior: 'smooth' });
		} else {
			showAlert(data.detail || 'Gagal membuat booking', 'error');
		}
	} catch (error) {
		showAlert('Koneksi gagal', 'error');
	} finally {
		btn.disabled = false;
		btn.innerHTML = '<i class="fas fa-check"></i> Pesan Shuttle';
	}
}

// Load my bookings
async function loadMyBookings() {
	try {
		const response = await fetch(`${API_URL}/api/bookings/my`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		const bookings = await response.json();
		
		const list = document.getElementById('booking-list');
		
		if (bookings.length === 0) {
			list.innerHTML = `
				<div class="empty-state">
					<i class="fas fa-inbox"></i>
					<p>Belum ada pemesanan</p>
				</div>
			`;
			// ✅ PERUBAHAN: Clear active drivers jika tidak ada booking
			activeDriverIds.clear();
			return;
		}
		
		list.innerHTML = bookings.map(b => `
			<div class="booking-item">
				<div class="booking-header">
					<span class="booking-id">#${b.booking_code || b.id}</span>
					<span class="status-badge status-${b.status}">${getStatusText(b.status)}</span>
				</div>
				<div class="booking-route">
					<strong>${b.from_location_name}</strong>
					<i class="fas fa-arrow-right"></i>
					<strong>${b.to_location_name}</strong>
				</div>
				${b.driver_name ? `
					<p style="margin-top: 10px;">
						<i class="fas fa-user"></i> Driver: ${b.driver_name}
						${b.driver_phone ? `<br><i class="fas fa-phone"></i> ${b.driver_phone}` : ''}
					</p>
				` : ''}
				${b.notes ? `<p><i class="fas fa-comment"></i> ${b.notes}</p>` : ''}
				<div class="booking-meta">
					<i class="fas fa-clock"></i> ${new Date(b.created_at).toLocaleString('id-ID')}
				</div>
				${getBookingActions(b)}
			</div>
		`).join('');
		
		// ✅ PERUBAHAN: Panggil fungsi tracking driver setelah render booking
		trackActiveDrivers(bookings);
		
	} catch (error) {
		showAlert('Gagal memuat riwayat', 'error');
	}
}

// Get booking actions
function getBookingActions(booking) {
	let actions = '';
	
	// Show cancel button for pending/accepted bookings
	if (booking.status === 'pending' || booking.status === 'accepted') {
		actions += `
			<button class="btn btn-danger" onclick="cancelBooking(${booking.id})" style="margin-top: 10px">
				<i class="fas fa-times"></i> Batalkan
			</button>
		`;
	}
	
	// Show track driver button for active bookings
	if (booking.driver_id && ['accepted', 'driver_arriving', 'ongoing'].includes(booking.status)) {
		actions += `
			<button class="btn btn-primary" onclick="trackDriver(${booking.driver_id})" style="margin-top: 10px; margin-left: 5px;">
				<i class="fas fa-map-marker-alt"></i> Lacak Driver
			</button>
		`;
	}
	
	return actions;
}

// Cancel booking
async function cancelBooking(bookingId) {
	if (!confirm('Yakin ingin membatalkan booking ini?')) return;
	
	try {
		const response = await fetch(`${API_URL}/api/bookings/${bookingId}/cancel`, {
			method: 'PUT',
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		const data = await response.json();
		
		if (response.ok && data.success) {
			showAlert('✅ Booking berhasil dibatalkan', 'success');
			loadMyBookings();
		} else {
			showAlert(data.detail || 'Gagal membatalkan booking', 'error');
		}
	} catch (error) {
		showAlert('Koneksi gagal', 'error');
	}
}

function getStatusText(status) {
	const statusMap = {
		'pending': 'Menunggu',
		'accepted': 'Diterima',
		'driver_arriving': 'Driver Dalam Perjalanan',
		'ongoing': 'Sedang Berjalan',
		'completed': 'Selesai',
		'cancelled': 'Dibatalkan',
		'no_show': 'Tidak Hadir'
	};
	return statusMap[status] || status;
}

// ==================== DRIVER TRACKING ====================

// ✅ PERUBAHAN: Fungsi tracking driver yang lebih robust
// Track active drivers on map
function trackActiveDrivers(bookings) {
	// Filter booking yang aktif dan punya driver
	const activeBookings = bookings.filter(b => 
		['accepted', 'driver_arriving', 'ongoing'].includes(b.status) && b.driver_id
	);
	
	// Update set active drivers
	const newActiveDriverIds = new Set(activeBookings.map(b => b.driver_id));
	
	// ✅ PERUBAHAN: Hapus marker driver yang sudah tidak aktif
	activeDriverIds.forEach(driverId => {
		if (!newActiveDriverIds.has(driverId)) {
			// Driver tidak lagi aktif, hapus marker-nya
			if (driverMarkers[driverId]) {
				map.removeLayer(driverMarkers[driverId]);
				delete driverMarkers[driverId];
			}
		}
	});
	
	// Update active driver IDs
	activeDriverIds = newActiveDriverIds;
	
	// ✅ PERUBAHAN: Fetch lokasi untuk setiap driver aktif
	activeDriverIds.forEach(driverId => {
		fetchDriverLocation(driverId);
	});
	
	// ✅ PERUBAHAN: Log untuk debugging
	if (activeDriverIds.size > 0) {
		console.log(`📍 Tracking ${activeDriverIds.size} active driver(s):`, Array.from(activeDriverIds));
	}
}

// ✅ PERUBAHAN: Fetch dengan error handling yang lebih baik
// Fetch and display driver location
async function fetchDriverLocation(driverId) {
	try {
		const response = await fetch(`${API_URL}/api/driver/current-location/${driverId}`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		if (!response.ok) {
			// ✅ PERUBAHAN: Jika 404, driver belum kirim lokasi
			if (response.status === 404) {
				console.log(`ℹ️ Driver ${driverId} belum mengirim lokasi GPS`);
			}
			return;
		}
		
		const location = await response.json();
		
		// ✅ PERUBAHAN: Validasi data lokasi sebelum update marker
		if (location && location.latitude && location.longitude) {
			updateDriverMarker(driverId, {
				latitude: location.latitude,
				longitude: location.longitude,
				speed: location.speed || 0,
				heading: location.heading || 0,
				timestamp: location.timestamp
			});
			console.log(`✅ Driver ${driverId} location updated:`, location.latitude, location.longitude);
		}
		
	} catch (error) {
		console.error(`❌ Error fetching driver ${driverId} location:`, error);
	}
}

// ✅ PERUBAHAN: Fungsi track driver yang lebih informatif
// Track specific driver
function trackDriver(driverId) {
	// Coba track di map
	const found = trackDriverOnMap(driverId, () => {
		// Callback jika driver tidak ditemukan di map
		showAlert('🔍 Mencari lokasi driver...', 'info');
		
		// Fetch lokasi driver
		fetchDriverLocation(driverId).then(() => {
			// Tunggu sebentar lalu coba track lagi
			setTimeout(() => {
				const retryFound = trackDriverOnMap(driverId);
				if (retryFound) {
					showAlert('📍 Driver ditemukan di peta', 'success');
				} else {
					showAlert('⚠️ Driver belum mengirim lokasi GPS. Pastikan driver sudah mengaktifkan GPS tracking.', 'error');
				}
			}, 1000);
		});
	});
	
	if (found) {
		showAlert('📍 Driver ditemukan di peta', 'success');
	}
}

// ✅ PERUBAHAN: Fungsi untuk start continuous tracking
function startDriverTracking() {
	// Stop existing interval jika ada
	if (driverTrackingInterval) {
		clearInterval(driverTrackingInterval);
	}
	
	// Update lokasi driver setiap 10 detik
	driverTrackingInterval = setInterval(() => {
		if (activeDriverIds.size > 0) {
			console.log(`🔄 Auto-updating ${activeDriverIds.size} driver location(s)...`);
			activeDriverIds.forEach(driverId => {
				fetchDriverLocation(driverId);
			});
		}
	}, 10000); // 10 detik
	
	console.log('✅ Driver tracking started (10s interval)');
}

// ✅ PERUBAHAN: Fungsi untuk stop tracking
function stopDriverTracking() {
	if (driverTrackingInterval) {
		clearInterval(driverTrackingInterval);
		driverTrackingInterval = null;
		console.log('⏹️ Driver tracking stopped');
	}
}

// ==================== WEBSOCKET ====================

// ✅ PERUBAHAN: WebSocket dengan reconnect yang lebih baik
// WebSocket for real-time updates
function initWebSocket() {
	const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
	const wsUrl = `${protocol}//${window.location.host}/ws/tracking`;
	
	try {
		ws = new WebSocket(wsUrl);
		
		ws.onopen = () => {
			console.log('✅ WebSocket connected');
		};
		
		ws.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				
				// ✅ PERUBAHAN: Handle location update dengan logging
				if (data.type === 'location_update' && data.driver_id) {
					console.log(`📡 WebSocket: Driver ${data.driver_id} location update received`);
					
					// Update hanya jika driver sedang aktif
					if (activeDriverIds.has(data.driver_id)) {
						updateDriverMarker(data.driver_id, {
							latitude: data.latitude,
							longitude: data.longitude,
							speed: data.speed,
							heading: data.heading || 0,
							timestamp: data.timestamp
						});
					}
				} else if (data.type === 'new_booking' || data.type === 'booking_update') {
					console.log('📡 WebSocket: Booking update received');
					loadMyBookings();
				}
			} catch (error) {
				console.error('❌ WebSocket message error:', error);
			}
		};
		
		ws.onerror = (error) => {
			console.error('❌ WebSocket error:', error);
		};
		
		ws.onclose = () => {
			console.log('📡 WebSocket disconnected, reconnecting in 5s...');
			setTimeout(initWebSocket, 5000);
		};
	} catch (error) {
		console.error('❌ WebSocket init error:', error);
		// Retry setelah 5 detik jika gagal
		setTimeout(initWebSocket, 5000);
	}
}

// ==================== INITIALIZATION ====================

// ✅ PERUBAHAN: Inisialisasi dengan tracking driver
// Initialize
setupMap();
loadLocations();
loadMyBookings(); // Ini akan trigger trackActiveDrivers()

// ✅ PERUBAHAN: Start tracking interval setelah load pertama
setTimeout(() => {
	startDriverTracking();
}, 2000); // Tunggu 2 detik setelah page load

// Init WebSocket
initWebSocket();

// ✅ PERUBAHAN: Refresh bookings setiap 30 detik (tetap ada untuk backup)
setInterval(() => {
	loadMyBookings(); // Ini akan update active drivers juga
}, 30000);

// ✅ PERUBAHAN: Hapus interval update driver yang lama, karena sudah diganti dengan startDriverTracking()
// Kode lama yang dihapus:
// setInterval(() => {
//   const driverIds = Object.keys(driverMarkers);
//   driverIds.forEach(driverId => {
//     fetchDriverLocation(parseInt(driverId));
//   });
// }, 10000);

// ✅ PERUBAHAN: Cleanup saat page unload
window.addEventListener('beforeunload', () => {
	stopDriverTracking();
	if (ws) ws.close();
});
