- [ ] Perbaiki `test_api.py` <br>
Reproduce: 
```bash
$ python3 main.py [IP] [PORT]
```
```bash
$ python3 test/test_api.py

╔════════════════════════════════════════════════════════════╗
║                                                            ║
║       🧪 UISI SHUTTLE API - TEST SUITE 🧪                 ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝


============================================================
  TEST 1: Server Connection
============================================================
❌ Cannot connect to server!
   Make sure backend is running: python main.py

❌ Cannot continue - server not running
``` 
<br>

- [ ] Perbaiki `update_coordinates.py` <br>
Apakah perlu:
```
KOORDINAT_BARU = {
    # CONTOH - Ganti dengan koordinat real dari Google Maps!
    # "Pos P13": (-7.1633, 112.6280),
    # "PPS": (-7.1645, 112.6275),
    # "Ged 1 A": (-7.1650, 112.6285),
    # "Ged 1 B": (-7.1655, 112.6290),
    # "POTK": (-7.1640, 112.6295),
    # "K3": (-7.1648, 112.6300),
    # "POS 1 SIG": (-7.1638, 112.6310),
    # "Wiragraha": (-7.1652, 112.6288),
    
    # Uncomment dan update koordinat di atas!
    # Atau tambahkan satu per satu seperti ini:
    # "Pos P13": (-7.XXXX, 112.XXXX),
}
```
<br>

- [ ] `Admin` Hapus Tipe
- [ ] `Admin` Ubah warna tombol merah ke ungu ke biru-an
- [ ] `Admin` Ubah "Total Booking Hari Ini" ke "Booking yang belum diterima"
- [ ] `Admin` Tambah peta di halaman admin
- [ ] `Driver` Driver tidak bisa mendeteksi lokasi pengguna
- [ ] `Driver` Driver tidak terdeteksi di peta
 
- [ ] Tambahkan dokumentasi di dalam kode
