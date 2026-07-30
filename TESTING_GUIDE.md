# Panduan Struktur & Pemeliharaan Testing (Testing Guide)

Dokumen ini ditujukan untuk Software Quality Assurance (QA) atau Automation Engineer yang akan membaca, memodifikasi, dan menambahkan test case baru ke dalam *framework* ini. Tujuan utamanya adalah menjaga agar kode tetap rapi (maintainable), mudah dibaca (readable), dan tidak ada duplikasi.

---

## 1. Penjelasan Struktur Folder & File

Bagi yang baru pertama kali melihat *framework* ini, jangan bingung. Berikut adalah peran dari masing-masing folder agar kamu tahu harus mencari file di mana:

* **`api/`**: Berisi *client* dan daftar URL/Endpoint API yang akan dites. Jika URL berubah, ubahlah di sini.
* **`collections/`**: Tempat menyimpan dokumen referensi, khususnya file Excel (`test_script.xlsx`) yang berisi daftar ratusan Test Case.
* **`config/`**: Pengaturan lingkungan (*environment variables*), seperti mengatur *token* atau kredensial.
* **`db/`**: Berisi *script* untuk koneksi ke Database PostgreSQL dan kumpulan *query SQL* untuk mengecek data secara langsung ke DB.
* **`evidence/`**: Folder penyimpanan sementara untuk bukti gambar (*screenshot* web ACS/FMS atau hasil *scan* QR e-Polis).
* **`flows/`**: Tempat menyimpan urutan proses atau skenario dari awal sampai akhir (End-to-End). Alur bisnis berulang diletakkan di sini agar kode tidak di-*copy-paste*.
* **`logs/`**: Menyimpan catatan aktivitas sistem (*log text*) selama *testing* berjalan untuk mempermudah pencarian error (*debugging*).
* **`payloads/`**: Berisi *template* format JSON standar untuk *request* API. Isinya hanya kerangka/dummy yang nilainya akan diisi otomatis oleh kode.
* **`reports/`**: **Folder Hasil Akhir!** Di sinilah Berita Acara (BA) hasil pengujian dalam format PDF, Word, Excel, dan HTML otomatis muncul setelah selesai.
* **`scripts/`**: Kumpulan *script* bantuan independen, misalnya *script* untuk men-generate payload massal.
* **`templates/`**: Kerangka desain (HTML/Jinja2) untuk mempercantik bentuk laporan PDF/Word yang digenerate.
* **`tests/`**: **Jantung Pengujian!** Di folder ini semua skenario dieksekusi menggunakan *pytest*. Penjelasan detailnya ada di bab selanjutnya.
* **`utils/`**: Berisi alat-alat pembantu (*helper*), seperti alat pembuat KTP palsu yang valid, *evidence collector*, dan pengubah HTML ke PDF.
* **`validators/`**: Tempat menaruh logika untuk memvalidasi/memastikan kebenaran data (Validasi DB dan Validasi UI/Web).

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
