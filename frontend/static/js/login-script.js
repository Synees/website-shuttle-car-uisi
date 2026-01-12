const API_URL = window.location.origin;

function switchTab(tab) {
	// Switch active tab
	document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
	document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
	
	if (tab === 'mahasiswa') {
		document.querySelectorAll('.tab')[0].classList.add('active');
		document.getElementById('mahasiswa-form').classList.add('active');
	} else {
		document.querySelectorAll('.tab')[1].classList.add('active');
		document.getElementById('staff-form').classList.add('active');
	}
	
	hideAlert();
}

function showAlert(message, type = 'error') {
	const alert = document.getElementById('alert');
	alert.textContent = message;
	alert.className = `alert alert-${type} show`;
}

function hideAlert() {
	document.getElementById('alert').classList.remove('show');
}

async function loginMahasiswa(event) {
	event.preventDefault();
	
	const email = document.getElementById('mahasiswa-email').value;
	const btn = document.getElementById('btn-mahasiswa');
	
	// Validasi email domain
	if (!email.endsWith('@student.uisi.ac.id')) {
		showAlert('Email harus menggunakan domain @student.uisi.ac.id', 'error');
		return;
	}
	
	btn.disabled = true;
	btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
	
	try {
		const response = await fetch(`${API_URL}/api/auth/login`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({email})
		});
		
		const data = await response.json();
		
		if (response.ok && data.success) {
			localStorage.setItem('token', data.token);
			localStorage.setItem('user', JSON.stringify(data.user));
			showAlert('Login berhasil! Mengalihkan...', 'success');
			setTimeout(() => window.location.href = '/pengguna.html', 1000);
		} else {
			showAlert(data.detail || 'Login gagal', 'error');
		}
	} catch (error) {
		showAlert('Koneksi gagal. Pastikan server berjalan.', 'error');
	} finally {
		btn.disabled = false;
		btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Masuk sebagai Mahasiswa';
	}
}

async function loginStaff(event) {
	event.preventDefault();
	
	const email = document.getElementById('staff-email').value;
	const password = document.getElementById('staff-password').value;
	const btn = document.getElementById('btn-staff');
	
	btn.disabled = true;
	btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Memproses...';
	
	try {
		const response = await fetch(`${API_URL}/api/auth/login`, {
			method: 'POST',
			headers: {'Content-Type': 'application/json'},
			body: JSON.stringify({email, password})
		});
		
		const data = await response.json();
		
		if (response.ok && data.success) {
			localStorage.setItem('token', data.token);
			localStorage.setItem('user', JSON.stringify(data.user));
			showAlert('Login berhasil! Mengalihkan...', 'success');
			
			// Redirect based on role
			const redirectUrl = data.user.role === 'admin' ? '/admin.html' : '/driver.html';
			setTimeout(() => window.location.href = redirectUrl, 1000);
		} else {
			showAlert(data.detail || 'Login gagal', 'error');
		}
	} catch (error) {
		showAlert('Koneksi gagal. Pastikan server berjalan.', 'error');
	} finally {
		btn.disabled = false;
		btn.innerHTML = '<i class="fas fa-sign-in-alt"></i> Login';
	}
}

