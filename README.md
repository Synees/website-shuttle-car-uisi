# Website Shuttle Car UISI
Sistem tracking shuttle kampus real-time untuk **Universitas Internasional Semen Indonesia (UISI)** dengan fitur permintaan fleksibel via WhatsApp.
```
uisi-shuttle-tracking/
│
├── README.md                          # Dokumentasi utama (baca dulu!)
├── requirements.txt                   # Python dependencies
├── .gitignore                        # Git ignore file
│
├── backend/
│   ├── main.py                       # Backend utama (FastAPI)
│   ├── setup_database.py             # Setup database & rute UISI
│   ├── config.py                     # Konfigurasi
│   ├── models.py                     # Database models
│   ├── utils.py                      # Helper functions
│   └── shuttle.db                    # SQLite database (auto-generated)
│
├── frontend/
│   ├── index.html                    # Halaman mahasiswa (tracking)
│   ├── driver.html                   # Halaman driver (GPS tracker)
│   ├── admin.html                    # Halaman admin (manage)
│   ├── css/
│   │   └── style.css                 # Styling
│   └── js/
│       ├── mahasiswa.js              # JS untuk mahasiswa
│       ├── driver.js                 # JS untuk driver
│       └── admin.js                  # JS untuk admin
│
├── tests/
│   ├── test_api.py                   # Test API endpoints
│   └── test_flow.py                  # Test full workflow
│
├── scripts/
│   ├── update_coordinates.py         # Update GPS coordinates
│   ├── backup_database.py            # Backup database
│   └── reset_database.py             # Reset database
│
└── docs/
    ├── API_DOCUMENTATION.md          # API docs lengkap
    ├── SETUP_GUIDE.md                # Panduan setup
    ├── USER_GUIDE.md                 # Panduan pengguna
    └── DEPLOYMENT.md                 # Panduan deployment
```
## 🚀 Quick Start (5 Menit!)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Setup Database
```bash
cd backend
python setup_database.py
```

### Step 3: Jalankan Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server jalan di: **http://localhost:8000**

### Step 4: Buka Frontend
- Mahasiswa: http://localhost:8000/
- Driver: http://localhost:8000/driver.html
- Admin: http://localhost:8000/admin.html

## 📍 PENTING: Update Koordinat GPS!

Koordinat yang saya gunakan adalah **ESTIMASI**. Anda HARUS update:
```bash
cd scripts
python update_coordinates.py
```

Cara cari koordinat:
1. Buka Google Maps
2. Cari lokasi kampus UISI
3. Klik kanan → "What's here?"
4. Copy koordinat (contoh: -7.1633, 112.6280)
5. Update di `update_coordinates.py`

## 📱 Cara Pakai

### Untuk Driver:
1. Cari IP komputer server: `ipconfig` (Windows) atau `ifconfig` (Mac/Linux)
2. Buka browser HP: `http://[IP]:8000/driver.html`
3. Klik START TRACKING
4. Izinkan akses lokasi

### Untuk Mahasiswa:
1. Buka browser: `http://[IP]:8000/`
2. Lihat posisi shuttle real-time
3. Lihat ETA ke setiap lokasi

### Untuk Admin:
1. Buka: `http://[IP]:8000/admin.html`
2. Input request dari grup WhatsApp
3. Manage rute & lihat history

## 📚 Dokumentasi Lengkap

Lihat folder `docs/` untuk dokumentasi detail:
- `SETUP_GUIDE.md` - Setup lengkap step by step
- `API_DOCUMENTATION.md` - API reference
- `USER_GUIDE.md` - Panduan pengguna
- `DEPLOYMENT.md` - Deploy ke production

## 🧪 Testing
```bash
cd tests
python test_api.py
```

## 🛠️ Troubleshooting

**Server tidak bisa diakses dari HP:**
- Pastikan WiFi sama
- Check firewall (allow port 8000)
- Gunakan IP address yang benar

**GPS tidak akurat:**
- Keluar ruangan (outdoor)
- Enable "High Accuracy" di settings
- Tunggu GPS lock (10-20 detik)

**Database error:**
```bash
cd scripts
python reset_database.py
```

## 📧 Support

Baca dokumentasi di folder `docs/` atau check API docs: http://localhost:8000/docs

---

**Developed for UISI - Universitas Internasional Semen Indonesia** 🎓
