const API_URL = window.location.origin;
const token = localStorage.getItem('token');
const user = JSON.parse(localStorage.getItem('user') || '{}');

let selectedScheduleFile = null;

// Check auth
if (!token || user.role !== 'admin') {
	window.location.href = '/';
}

function showAlert(message, type = 'error') {
	const alert = document.getElementById('alert');
	alert.textContent = message;
	alert.className = `alert alert-${type} show`;
	setTimeout(() => alert.classList.remove('show'), 5000);
}

function logout() {
	localStorage.clear();
	window.location.href = '/';
}

function switchTab(tab) {
	document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
	document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
	
	event.target.classList.add('active');
	document.getElementById(`tab-${tab}`).classList.add('active');
	
	if (tab === 'locations') loadLocations();
	else if (tab === 'bookings') loadBookings();
	else if (tab === 'users') loadUsers();
	else if (tab === 'schedule') loadScheduleStatus();
}

// Load stats
async function loadStats() {
	try {
		const response = await fetch(`${API_URL}/api/admin/stats`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		const stats = await response.json();
		document.getElementById('stat-today').textContent = stats.today_bookings;
		document.getElementById('stat-accepted').textContent = stats.accepted_bookings;
	} catch (error) {
		console.error('Error loading stats:', error);
	}
}

// Load all bookings
async function loadBookings() {
	try {
		const response = await fetch(`${API_URL}/api/admin/bookings`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		const bookings = await response.json();
		
		const tbody = document.getElementById('bookings-tbody');
		
		if (bookings.length === 0) {
			tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 40px;">Belum ada booking</td></tr>';
			return;
		}
		
		tbody.innerHTML = bookings.map(b => `
			<tr>
				<td>#${b.id}</td>
				<td>${b.user_name}<br><small>${b.user_email}</small></td>
				<td>${b.from_location_name}</td>
				<td>${b.to_location_name}</td>
				<td>${b.driver_name || '-'}</td>
				<td><span class="status-badge status-${b.status}">${getStatusText(b.status)}</span></td>
				<td>${new Date(b.created_at).toLocaleString('id-ID')}</td>
			</tr>
		`).join('');
	} catch (error) {
		showAlert('Gagal memuat booking', 'error');
	}
}

function getStatusText(status) {
	const map = {
		'pending': 'Menunggu',
		'accepted': 'Diterima',
		'driver_arriving': 'Driver OTW',
		'ongoing': 'Berjalan',
		'completed': 'Selesai',
		'cancelled': 'Dibatalkan'
	};
	return map[status] || status;
}

// Load locations
async function loadLocations() {
	try {
		const response = await fetch(`${API_URL}/api/locations`);
		const locations = await response.json();
		
		const tbody = document.getElementById('locations-tbody');
		tbody.innerHTML = locations.map(loc => `
			<tr>
				<td>${loc.id}</td>
				<td><strong>${loc.name}</strong><br><small>${loc.description || ''}</small></td>
				<td>${loc.latitude.toFixed(5)}, ${loc.longitude.toFixed(5)}</td>
				<td>${loc.type}</td>
				<td>${loc.status}</td>
				<td>
					<button class="btn btn-primary btn-sm" onclick='editLocation(${JSON.stringify(loc)})'>
						<i class="fas fa-edit"></i> Edit
					</button>
					<button class="btn btn-danger btn-sm" onclick="deleteLocation(${loc.id})">
						<i class="fas fa-trash"></i> Hapus
					</button>
				</td>
			</tr>
		`).join('');
	} catch (error) {
		showAlert('Gagal memuat lokasi', 'error');
	}
}

function showAddLocationModal() {
	document.getElementById('modal-title').textContent = 'Tambah Lokasi Baru';
	document.getElementById('location-id').value = '';
	document.getElementById('location-name').value = '';
	document.getElementById('location-desc').value = '';
	document.getElementById('location-lat').value = '';
	document.getElementById('location-lng').value = '';
	document.getElementById('location-type').value = 'pickup';
	document.getElementById('location-modal').classList.add('show');
}

function editLocation(loc) {
	document.getElementById('modal-title').textContent = 'Edit Lokasi';
	document.getElementById('location-id').value = loc.id;
	document.getElementById('location-name').value = loc.name;
	document.getElementById('location-desc').value = loc.description || '';
	document.getElementById('location-lat').value = loc.latitude;
	document.getElementById('location-lng').value = loc.longitude;
	document.getElementById('location-type').value = loc.type;
	document.getElementById('location-modal').classList.add('show');
}

function closeLocationModal() {
	document.getElementById('location-modal').classList.remove('show');
}

async function saveLocation(event) {
	event.preventDefault();
	
	const id = document.getElementById('location-id').value;
	const data = {
		name: document.getElementById('location-name').value,
		description: document.getElementById('location-desc').value,
		latitude: parseFloat(document.getElementById('location-lat').value),
		longitude: parseFloat(document.getElementById('location-lng').value),
		type: document.getElementById('location-type').value
	};
	
	try {
		const url = id ? `${API_URL}/api/admin/locations/${id}` : `${API_URL}/api/admin/locations`;
		const method = id ? 'PUT' : 'POST';
		
		const response = await fetch(url, {
			method,
			headers: {
				'Content-Type': 'application/json',
				'Authorization': `Bearer ${token}`
			},
			body: JSON.stringify(data)
		});
		
		const result = await response.json();
		
		if (response.ok && result.success) {
			showAlert(`Lokasi berhasil ${id ? 'diupdate' : 'ditambahkan'}`, 'success');
			closeLocationModal();
			loadLocations();
		} else {
			showAlert(result.detail || 'Gagal menyimpan lokasi', 'error');
		}
	} catch (error) {
		showAlert('Koneksi gagal', 'error');
	}
}

async function deleteLocation(id) {
	if (!confirm('Yakin ingin menghapus lokasi ini?')) return;
	
	try {
		const response = await fetch(`${API_URL}/api/admin/locations/${id}`, {
			method: 'DELETE',
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		const result = await response.json();
		
		if (response.ok && result.success) {
			showAlert('Lokasi berhasil dihapus', 'success');
			loadLocations();
		} else {
			showAlert(result.detail || 'Gagal menghapus lokasi', 'error');
		}
	} catch (error) {
		showAlert('Koneksi gagal', 'error');
	}
}

// ==================== FUNGSI LIST PENGGUNA ====================

async function loadUsers() {
	try {
		const response = await fetch(`${API_URL}/api/admin/users`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		if (!response.ok) {
			throw new Error('Failed to load users');
		}
		
		const users = await response.json();
		const tbody = document.getElementById('users-tbody');
		
		if (users.length === 0) {
			tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px;">Belum ada pengguna terdaftar</td></tr>';
			return;
		}
		
		tbody.innerHTML = users.map(u => `
			<tr>
				<td>${u.id}</td>
				<td>${u.email}</td>
				<td>${u.name || '-'}</td>
				<td>${u.nim || '-'}</td>
				<td><span class="booking-count">${u.total_bookings || 0}</span></td>
				<td>
					<button class="btn btn-primary btn-sm" onclick="showUserHistory(${u.id}, '${u.email}')">
						<i class="fas fa-history"></i> Histori
					</button>
					<button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id}, '${u.email}')">
						<i class="fas fa-trash"></i> Hapus
					</button>
				</td>
			</tr>
		`).join('');
	} catch (error) {
		console.error('Error loading users:', error);
		showAlert('Gagal memuat data pengguna', 'error');
	}
}

async function showUserHistory(userId, userEmail) {
	document.getElementById('history-modal').classList.add('show');
	document.getElementById('history-modal-title').textContent = `Histori Pemesanan - ${userEmail}`;
	document.getElementById('history-content').innerHTML = `
		<div style="text-align: center; padding: 40px;">
			<i class="fas fa-spinner fa-spin" style="font-size: 32px; color: #dc2626;"></i>
			<p style="margin-top: 15px;">Loading histori...</p>
		</div>
	`;
	
	try {
		const response = await fetch(`${API_URL}/api/admin/users/${userId}/bookings`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		if (!response.ok) {
			throw new Error('Failed to load history');
		}
		
		const bookings = await response.json();
		
		if (bookings.length === 0) {
			document.getElementById('history-content').innerHTML = `
				<div style="text-align: center; padding: 40px; color: #64748b;">
					<i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 15px; opacity: 0.3;"></i>
					<p>Belum ada histori pemesanan</p>
				</div>
			`;
			return;
		}
		
		document.getElementById('history-content').innerHTML = `
			<div class="history-list">
				${bookings.map(b => `
					<div class="history-item">
						<div class="history-header">
							<span class="booking-code">#${b.id}</span>
							<span class="status-badge status-${b.status}">${getStatusText(b.status)}</span>
						</div>
						<div class="history-route">
							<i class="fas fa-map-marker-alt" style="color: #10b981;"></i>
							<strong>${b.from_location_name}</strong>
							<i class="fas fa-arrow-right" style="margin: 0 10px; color: #64748b;"></i>
							<i class="fas fa-map-marker-alt" style="color: #ef4444;"></i>
							<strong>${b.to_location_name}</strong>
						</div>
						${b.driver_name ? `<div class="history-driver"><i class="fas fa-user"></i> Driver: ${b.driver_name}</div>` : ''}
						${b.notes ? `<div class="history-notes"><i class="fas fa-comment"></i> ${b.notes}</div>` : ''}
						<div class="history-date">
							<i class="fas fa-clock"></i> ${new Date(b.created_at).toLocaleString('id-ID')}
						</div>
					</div>
				`).join('')}
			</div>
		`;
	} catch (error) {
		console.error('Error loading history:', error);
		document.getElementById('history-content').innerHTML = `
			<div style="text-align: center; padding: 40px; color: #ef4444;">
				<i class="fas fa-exclamation-triangle" style="font-size: 48px; margin-bottom: 15px;"></i>
				<p>Gagal memuat histori pemesanan</p>
			</div>
		`;
	}
}

function closeHistoryModal() {
	document.getElementById('history-modal').classList.remove('show');
}

async function deleteUser(userId, userEmail) {
	const confirmation = prompt(
		`PERINGATAN: Menghapus akun akan menghapus semua data pengguna termasuk histori booking!\n\n` +
		`Ketik "${userEmail}" untuk konfirmasi penghapusan:`
	);
	
	if (confirmation !== userEmail) {
		if (confirmation !== null) {
			showAlert('Konfirmasi email tidak sesuai. Penghapusan dibatalkan.', 'error');
		}
		return;
	}
	
	try {
		const response = await fetch(`${API_URL}/api/admin/users/${userId}`, {
			method: 'DELETE',
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		const result = await response.json();
		
		if (response.ok && result.success) {
			showAlert('Akun pengguna berhasil dihapus', 'success');
			loadUsers();
		} else {
			showAlert(result.detail || 'Gagal menghapus akun', 'error');
		}
	} catch (error) {
		console.error('Error deleting user:', error);
		showAlert('Koneksi gagal', 'error');
	}
}

// ==================== FUNGSI KELOLA JADWAL ====================

// Show upload modal
function showUploadScheduleModal() {
	document.getElementById('schedule-modal').classList.add('show');
}

// Close modal
function closeScheduleModal() {
	document.getElementById('schedule-modal').classList.remove('show');
	// Reset form
	document.getElementById('schedule-file-input').value = '';
	document.getElementById('selected-file-info').style.display = 'none';
	document.getElementById('btn-upload-schedule').disabled = true;
	document.getElementById('btn-upload-schedule').style.opacity = '0.5';
}

// Load schedule status for navbar display
async function loadScheduleStatusText() {
	const statusText = document.getElementById('schedule-status-text');
	
	try {
		const response = await fetch(`${API_URL}/api/schedule/status`, {
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		const data = await response.json();
		
		if (data.exists) {
			statusText.innerHTML = `
				<i class="fas fa-check-circle" style="color: #10b981;"></i>
				<span style="color: #10b981;">${data.path}</span>
				<button class="btn btn-primary" onclick="viewScheduleAdmin()" style="margin-left: 10px; padding: 5px 10px; font-size: 12px;">
					<i class="fas fa-eye"></i> Lihat
				</button>
				<button class="btn btn-danger" onclick="deleteScheduleConfirm()" style="margin-left: 5px; padding: 5px 10px; font-size: 12px;">
					<i class="fas fa-trash"></i> Hapus
				</button>
			`;
		} else {
			statusText.innerHTML = `<i class="fas fa-exclamation-circle" style="color: #ef4444;"></i> <span style="color: #ef4444;">File jadwal tidak ada</span>`;
		}
	} catch (error) {
		console.error('Error loading schedule status:', error);
		statusText.innerHTML = `<i class="fas fa-times-circle" style="color: #ef4444;"></i> <span style="color: #ef4444;">Gagal memuat status</span>`;
	}
}

// Load schedule status (old function - keep for compatibility)
async function loadScheduleStatus() {
	loadScheduleStatusText();
}

// Handle file selection
function handleScheduleFileSelect(event) {
	const file = event.target.files[0];
	const uploadBtn = document.getElementById('btn-upload-schedule');
	const fileInfo = document.getElementById('selected-file-info');
	const fileName = document.getElementById('selected-file-name');
	
	if (!file) {
		selectedScheduleFile = null;
		uploadBtn.disabled = true;
		uploadBtn.style.opacity = '0.5';
		fileInfo.style.display = 'none';
		return;
	}
	
	// Validate file type
	if (file.type !== 'application/pdf') {
		showAlert('File harus berformat PDF!', 'error');
		event.target.value = '';
		selectedScheduleFile = null;
		uploadBtn.disabled = true;
		uploadBtn.style.opacity = '0.5';
		fileInfo.style.display = 'none';
		return;
	}
	
	// Validate file size (max 10MB)
	if (file.size > 10 * 1024 * 1024) {
		showAlert('Ukuran file maksimal 10MB!', 'error');
		event.target.value = '';
		selectedScheduleFile = null;
		uploadBtn.disabled = true;
		uploadBtn.style.opacity = '0.5';
		fileInfo.style.display = 'none';
		return;
	}
	
	selectedScheduleFile = file;
	uploadBtn.disabled = false;
	uploadBtn.style.opacity = '1';
	fileName.textContent = `${file.name} (${(file.size / 1024).toFixed(2)} KB)`;
	fileInfo.style.display = 'block';
}

// Upload schedule
async function uploadSchedule() {
	if (!selectedScheduleFile) {
		showAlert('Pilih file PDF terlebih dahulu!', 'error');
		return;
	}
	
	const uploadBtn = document.getElementById('btn-upload-schedule');
	const originalText = uploadBtn.innerHTML;
	
	uploadBtn.disabled = true;
	uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Mengupload...';
	
	try {
		const formData = new FormData();
		formData.append('file', selectedScheduleFile);
		
		const response = await fetch(`${API_URL}/api/admin/schedule/upload`, {
			method: 'POST',
			headers: {
				'Authorization': `Bearer ${token}`
			},
			body: formData
		});
		
		const data = await response.json();
		
		if (response.ok && data.success) {
			showAlert('✅ Jadwal berhasil diupload!', 'success');
			
			// Close modal and reload status
			closeScheduleModal();
			loadScheduleStatusText();
		} else {
			showAlert(data.detail || 'Gagal mengupload jadwal', 'error');
		}
	} catch (error) {
		console.error('Error uploading schedule:', error);
		showAlert('Koneksi gagal', 'error');
	} finally {
		uploadBtn.disabled = false;
		uploadBtn.innerHTML = originalText;
	}
}

// View schedule (admin)
function viewScheduleAdmin() {
	window.open(`${API_URL}/api/schedule`, '_blank');
}

// Delete schedule with confirmation
async function deleteScheduleConfirm() {
	if (!confirm('Yakin ingin menghapus file jadwal? Pengguna dan driver tidak akan bisa melihat jadwal.')) {
		return;
	}
	
	try {
		const response = await fetch(`${API_URL}/api/admin/schedule`, {
			method: 'DELETE',
			headers: {'Authorization': `Bearer ${token}`}
		});
		
		const data = await response.json();
		
		if (response.ok && data.success) {
			showAlert('✅ Jadwal berhasil dihapus', 'success');
			loadScheduleStatusText();
		} else {
			showAlert(data.detail || 'Gagal menghapus jadwal', 'error');
		}
	} catch (error) {
		console.error('Error deleting schedule:', error);
		showAlert('Koneksi gagal', 'error');
	}
}

// View schedule (old function - keep for compatibility)
function viewSchedule() {
	viewScheduleAdmin();
}

// Delete schedule (old function - keep for compatibility)
async function deleteSchedule() {
	await deleteScheduleConfirm();
}

// Initialize
loadStats();
loadBookings();
loadScheduleStatusText(); // Load schedule status on page load

// Refresh every 30 seconds
setInterval(() => {
	loadStats();
	loadBookings();
}, 30000);
