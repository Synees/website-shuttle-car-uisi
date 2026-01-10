# Website Shuttle Car UISI
Sistem tracking shuttle kampus real-time untuk **Universitas Internasional Semen Indonesia (UISI)**

## Struktur Folder
```
website-shuttle-car-uisi/
├── .venv
├── assets
│   └── jadwal.pdf
├── backend
│   └── setup_database.py
├── frontend
│   ├── admin.html
│   ├── driver.html
│   ├── login.html
│   ├── pengguna.html
│   └── static
│       ├── css
│       │   ├── admin-style.css
│       │   ├── driver-style.css
│       │   ├── login-style.css
│       │   └── pengguna-style.css
│       └── js
│           ├── admin-script.js
│           ├── driver-script.js
│           ├── login-script.js
│           ├── map-script.js
│           └── pengguna-script.js
├── generate_ssl.py
├── main.py
├── README.md
├── requirements.txt
├── scripts
│   ├── backup_database.py
│   ├── reset_database.py
│   └── update_coordinates.py
└── TODO.md

```

## Setup
### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Setup Database
```bash
cd backend
python setup_database.py
```

### Step 3: Setup https 
```bash
python generate_ssl.py
```

### Step 4: Cek ip address wireless
cek dibagian wireless <br>
Linux:
```
ip addr
```

Windows:
```
ifconfig
```

### Step 3: Jalankan Server
```bash
python main.py [IP] 8000
```

- Mahasiswa: https://[IP]:8000/
- Driver: https://[IP]8000/driver.html
- Admin: https://[IP]8000/admin.html

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

## 🧪 Testing
```bash
cd tests
python test_api.py
```
