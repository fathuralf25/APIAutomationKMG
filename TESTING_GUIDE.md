
# Panduan Struktur & Pemeliharaan Testing (Testing Guide)

Dokumen ini ditujukan untuk Software Quality Assurance (QA) atau Automation Engineer yang akan membaca, memodifikasi, dan menambahkan test case baru ke dalam *framework* ini. Tujuan utamanya adalah menjaga agar kode tetap rapi (maintainable), mudah dibaca (readable), dan tidak ada duplikasi.

---

## 1. Penjelasan Struktur Folder & File

Bagi yang baru pertama kali melihat *framework* ini, jangan bingung. Berikut adalah peran dari masing-masing folder agar kamu tahu harus mencari file di mana:

* **`api/`**: Berisi *client* dan daftar URL/Endpoint API yang akan dites. Jika URL berubah, ubahlah di sini.
  * `client.py`: Mengatur koneksi HTTP dan autentikasi (token/JWT) ke server API.
  * `endpoints.py`: Menyimpan daftar URL endpoint API (seperti submit draft, inquiry loan, dll).
* **`collections/`**: Tempat menyimpan dokumen referensi, khususnya file Excel (`test_script.xlsx`) yang berisi daftar ratusan Test Case.
  * `test_script.xlsx`: File utama yang memuat skenario Test Case untuk otomatisasi.
  * `base_template.docx` & `TEMPLATE_Defect Report.docx`: Template mentah Microsoft Word untuk pembuatan laporan hasil dan defect.
* **`config/`**: Pengaturan lingkungan (*environment variables*), seperti mengatur *token* atau kredensial.
  * `config.py`: Script untuk memuat variabel dari `.env` dan menyediakannya untuk digunakan oleh file lain.
* **`db/`**: Berisi *script* untuk koneksi ke Database PostgreSQL dan kumpulan *query SQL* untuk mengecek data secara langsung ke DB.
  * `client.py`: Mengatur koneksi ke database menggunakan `psycopg2`.
  * `queries.py`: Berisi query SQL terpusat (contoh: query cek status aplikasi berdasarkan KTP).
* **`evidence/`**: Folder penyimpanan sementara untuk bukti gambar (*screenshot* web ACS/FMS atau hasil *scan* QR e-Polis).
  * `acs/`: Sub-folder untuk menampung screenshot dari aplikasi web ACS/FMS.
* **`flows/`**: Tempat menyimpan urutan proses atau skenario dari awal sampai akhir (End-to-End). Alur bisnis berulang diletakkan di sini agar kode tidak di-*copy-paste*.
  * `e2e_flow.py`: Mengatur alur end-to-end (Submit -> Inquiry -> Otorisasi -> Pembayaran).
* **`logs/`**: Menyimpan catatan aktivitas sistem (*log text*) selama *testing* berjalan untuk mempermudah pencarian error (*debugging*).
  * `execution_*.log`: File text yang mencatat setiap request, response, error, dan informasi debug.
* **`payloads/`**: Berisi *template* format JSON standar untuk *request* API. Isinya hanya kerangka/dummy yang nilainya akan diisi otomatis oleh kode.
  * `submit_draft_akseptasi.json`, `inquiry_nomor_loan.json`, dll: File JSON mentah sebagai kerangka (template) body request.
* **`reports/`**: **Folder Hasil Akhir!** Di sinilah Berita Acara (BA) hasil pengujian dalam format PDF, Word, Excel, dan HTML otomatis muncul setelah selesai.
  * Berisi *output* laporan seperti `Automation_Report_Batch_*.docx`, `*.html`, `*.xlsx`, serta hasil tangkapan/validasi dokumen.
* **`scripts/`**: Kumpulan *script* bantuan independen, misalnya *script* untuk men-generate payload massal.
  * `generate_payloads.py`: Script bantuan eksternal untuk generate payload secara massal/spesifik.
  * `query_db.py`: Script untuk test query ke DB langsung tanpa menjalankan pytest.
  * `setup_template.py`: Script untuk mempersiapkan template file dari awal.
* **`templates/`**: Kerangka desain (HTML/Jinja2) untuk mempercantik bentuk laporan PDF/Word yang digenerate.
  * `report_template.html`: Layout dan styling HTML untuk dirender ke dalam bentuk PDF laporan akhir.
* **`tests/`**: **Jantung Pengujian!** Di folder ini semua skenario dieksekusi menggunakan *pytest*. Penjelasan detailnya ada di bab selanjutnya.
  * `test_all_scenarios.py`: Menjalankan semua skenario pengujian membaca dari excel.
  * `test_run_selected.py`: Menjalankan sebagian / 1 test case untuk debugging.
  * `test_sandbox.py`: Tempat eksperimen API / logic sebelum dimasukkan ke flow utama.
  * `conftest.py`: Pengaturan dasar *pytest* untuk semua test, termasuk penanganan log & laporan akhir.
  * `test_unit.py`: Skrip untuk menguji keandalan *utility* dan *helper* mandiri.
* **`utils/`**: Berisi alat-alat pembantu (*helper*), seperti alat pembuat KTP palsu yang valid, *evidence collector*, dan pengubah HTML ke PDF.
  * `evidence_collector.py`: Mengumpulkan data bukti (response API, screenshot, query db) dari setiap test.
  * `generators.py`: Generator data dummy/dinamis (KTP, tanggal, dsb).
  * `logger.py`: Konfigurasi format pencatatan *log* (menggunakan logging standar Python).
  * `payload_factory.py`: Mengisi nilai dinamis ke dalam file JSON di folder `payloads`.
  * `payload_loader.py`: Memuat dan membaca file JSON `payloads` menjadi format dict.
  * `qr_scanner.py`: Utilitas untuk memindai kode QR dari gambar e-Polis.
  * `report_generator.py`: Menyusun evidence yang terkumpul ke dalam dokumen Excel/Word/HTML/PDF.
  * `ui_acs.py`: Skrip otomatisasi (misal Playwright/Selenium) untuk interaksi halaman web ACS.
* **`validators/`**: Tempat menaruh logika untuk memvalidasi/memastikan kebenaran data (Validasi DB dan Validasi UI/Web).
  * `db_validator.py`: Mengandung fungsi assert yang membandingkan response API/kondisi awal dengan data riil di PostgreSQL.
  * `ui_validator.py`: Mengecek tampilan antarmuka (misalnya tulisan/status di aplikasi web).

---

## 2. Arsitektur Folder `tests/` (Jantung Pengujian)

Semua script testing menggunakan `pytest` dan berada di dalam folder `tests/`.

* **`tests/test_all_scenarios.py`** (Script Utama)
  * Membaca test case langsung dari Excel (`collections/test_script.xlsx`).
  * Mengeksekusi skenario *positive* dan *negative* secara dinamis berdasarkan data Excel.
  * Menangani alur End-to-End (E2E) dan otomatis menjaga relasi data (seperti `nomor_transaksi` dan `nomor_loan`) untuk *hit* API secara berurutan.
* **`tests/test_run_selected.py`**
  * Digunakan untuk menjalankan TC tertentu saja (misal: TC-29) dari Excel, tanpa mengeksekusi semua baris.
  * Sangat berguna untuk *debugging* atau *re-test* satu skenario spesifik secara cepat.
  * Menggunakan fungsi dan alur yang sama persis dengan `test_all_scenarios.py` sehingga anti-duplikasi.
* **`tests/test_sandbox.py`**
  * Digunakan sebagai "tempat bermain" (sandbox) untuk mencoba skenario *edge-case* baru secara *step-by-step* (hardcode manual). Setelah selesai dan matang, logikanya bisa dipindah ke flow utama.
* **`tests/conftest.py`**
  * Menyimpan konfigurasi global `pytest`. Di sinilah fitur pembersihan *log* otomatis dan *trigger* untuk menjalankan *Report Generator* diletakkan (berjalan setelah semua test selesai - `pytest_sessionfinish`).

---

## 3. Cara Kerja Data & Payload (PENTING!)

**ATURAN EMAS:** JANGAN PERNAH *HARDCODE* NILAI BISNIS DI DALAM FILE TEST ATAU JSON!

1. **File JSON di `payloads/` HANYA BERUPA TEMPLATE.**
   * File JSON ini hanya berisi struktur/kerangka dasar *request*.
2. **Gunakan `utils/payload_factory.py` atau `utils/data_generator.py`.**
   * Setiap nilai dinamis (seperti `nomor_transaksi`, `ktp`, `tenor`, dll) harus di-*generate* secara dinamis sebelum *request* dikirimkan.
   * Hal ini memastikan pengujian dapat dijalankan berulang-ulang tanpa masalah data duplikat di Database (PostgreSQL).

---

## 4. Alur End-To-End (State & Data Relationship)

Sistem Askrindo KMG Jatim memiliki aturan ketat terkait *flow*. Anda tidak bisa melakukan "Pembayaran" jika belum melakukan "Submit Draft" dan "Inquiry".

Bagaimana framework ini menanganinya?

* Di dalam `test_all_scenarios.py`, kita menggunakan variabel dictionary `state` (di-*pass* via *fixture* pytest).
* Setiap kali "Submit Draft" sukses, `nomor_transaksi` akan disimpan di `state["last_success_trx"]`.
* Saat test case selanjutnya berjalan (misal: "Inquiry Loan"), fungsi pembuat payload akan otomatis mengambil `nomor_transaksi` dari `state` tersebut, sehingga data yang digunakan akan saling berkesinambungan.

---

## 5. Evidence & Reporting (Bukti Pengujian)

Framework ini dirancang untuk tidak sekadar "Hit API lalu Assert 200", melainkan mencetak **Berita Acara (BA)** layaknya SIT/UAT Enterprise.

Semua bukti dikumpulkan menggunakan class **`EvidenceCollector`** (`utils/evidence_collector.py`).

### Cara Mengumpulkan Bukti di dalam Test:

```python
# 1. Daftarkan Test Case
evidence_collector.set_test_metadata(tc_id, "Nama Test", "Expected", "Precondition")

# 2. Tambahkan Bukti API
evidence_collector.add_api_evidence(tc_id, ENDPOINT, "POST", payload, response.json(), 200)

# 3. Tambahkan Bukti Database
evidence_collector.add_db_evidence(tc_id, "Query Cek Draft", db_result)

# 4. Tambahkan Bukti E-Polis (Screenshot & Scan QR)
evidence_collector.add_epolis_evidence(tc_id, qr_result, image_paths)
```

### Pembuatan Laporan Otomatis:

Setelah tes selesai, `utils/report_generator.py` akan dipanggil otomatis dan mengubah kumpulan bukti (`evidence_collector.evidences`) menjadi:

* **HTML & PDF:** Menggunakan Jinja2 (`templates/report_template.html`) + WeasyPrint.
* **DOCX:** Menggunakan `python-docx` (Memasukkan tabel, gambar e-polis, formatting).
* **XLSX:** Menulis langsung status "Passed/Failed" dan "Test Data" ke file Excel.

---

## 6. Menambahkan Test Case Baru (Best Practices)

Jika Anda ingin menambahkan skenario baru:

**Jika skenario tersebut adalah skenario reguler (Excel):**

1. Buka `collections/test_script.xlsx`.
2. Tambahkan baris baru dengan format ID `TC-XX`.
3. Jalankan `pytest tests/test_all_scenarios.py`. Sistem akan otomatis mendeteksi dan menjalankannya!

**Jika skenario tersebut adalah eksperimen baru / edge-case yang kompleks:**

1. Buka `tests/test_sandbox.py` jika Anda perlu melakukan *trial and error* API-nya secara manual (sandbox test).
2. Jika skenarionya sudah matang, masukkan TC tersebut ke `collections/test_script.xlsx` dan atur datanya di `utils/payload_factory.py`.
3. Untuk tahap *debugging*, gunakan `tests/test_run_selected.py` dan ubah variabel `SELECTED_TC` dengan ID TC tersebut untuk menjalankannya secara terisolasi tanpa menyentuh file utama.

**Catatan Maintanability:**

* Selalu gunakan fungsi pembantu di `utils/` jika memungkinkan.
* Jika Anda merubah tampilan laporan (misal: mengecilkan gambar E-Polis), ubahlah di `utils/report_generator.py` (untuk DOCX) atau `templates/report_template.html` (untuk HTML/PDF). Jangan lakukan *hardcode* di dalam script test.
