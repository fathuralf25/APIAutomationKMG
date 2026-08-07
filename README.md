# Enterprise QA Automation Platform - API KMG Jatim

This project is an Enterprise-level API Automation Framework designed for the KMG Jatim integration. It goes beyond simple API testing by validating complete business flows, ensuring database consistency, generating comprehensive reports (PDF, HTML, Word, Excel), and validating UI (ACS) interactions.

## 🚀 Tech Stack

- **Python 3.x**
- **pytest** - Core testing framework
- **requests** - API interactions
- **psycopg2** - PostgreSQL database validation
- **python-dotenv** - Environment variables management
- **openpyxl / python-docx / weasyprint** - Auto-generating BA (Berita Acara), Excel scripts, and PDF reports.
- **playwright** - UI validation / E-Polis generation checking.

## 📂 Project Structure

```
├── api/          # API Client and endpoint wrappers
├── collections/  # Core templates for reporting (Excel, Word)
├── config/       # Environment variables and configurations
├── db/           # PostgreSQL Client and DB validation queries
├── payloads/     # JSON Templates for API requests
├── reports/      # Auto-generated reports (HTML, PDF, DOCX, XLSX)
├── tests/        # Pytest test suites (scenarios)
├── utils/        # Helpers (Data generator, Logger, Evidence Collector, etc.)
├── requirements.txt
└── pytest.ini
```

## ⚙️ Installation & Setup

1. **Clone the repository.**
2. **Create and activate a virtual environment (optional but recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or .venv\Scripts\activate on Windows
   ```
3. **Install all dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Install Playwright browsers (if you need UI validations):**
   ```bash
   playwright install
   ```
5. **Configure Environment Variables:**
   Create and setup your `.env` file in the root directory (Database credentials, API URL, Tokens).

## 🔄 Business Flow & API Scenarios

This framework validates the API end-to-end based on the strict KMG Jatim Business Rules:

1. **Hit Kalkulator Premi (Optional):**
   Validate `uang_pertanggungan`, `tenor`, and get instant `premi` calculations.
2. **Submit Draft Akseptasi:**
   Creates a new application draft.

   - Uses generated dynamic fields (`nomor_transaksi` with `AKS-YYYYMMDD-HHMMSS` format).
   - Validates KTP rules (a single KTP cannot have multiple active submissions).
   - Validates Age limits (18 - 65 years).
3. **Inquiry Loan:**

   - Validates that `nomor_loan` and `nomor_perjanjian_kredit` are unique.
   - Cross-checks that `tanggal_akad` is not later than `tanggal_rencana_realisasi`.
4. **Otorisasi Penyelia:**
   Approves the loan using `nomor_transaksi` and `nomor_loan` generated from the previous steps.
5. **Pembayaran Premi:**
   Validates premium payments where `nominal_pembayaran` must match the `premi` returned in step 2. Uses a unique `nomor_reff_pembayaran`.
6. **Pembatalan Akseptasi (Cancellation):**
   Validates that cancellation can only happen if the application status allows it (Status Akseptasi = 9). Once canceled, the KTP can be reused.

## ▶️ Running the Tests

**📖 Important:** Before adding new tests or modifying existing ones, please read the [TESTING_GUIDE.md](file:///Users/fathur/QA/automation-api-kmgjatim/TESTING_GUIDE.md) to understand the architecture, payload handling, and report generation structure.

**Run using the Interactive Script (Recommended):**

We now use an interactive runner `run_test.py` at the root of the project which allows you to dynamically set the Project Code, Report Title, and choose whether to run all scenarios or just specific ones (e.g. TC-31).

```bash
python run_test.py
```

**Run via pytest command directly:**

```bash
pytest tests/test_all_scenarios.py -v
```

**Sandbox Experimentation:**
To manually experiment with new scenarios step-by-step before they are fully automated, use the `tests/test_sandbox.py` file.

**What happens after execution?**

- The framework automatically records the full payloads, API responses, and Database results in memory.
- Old log files are automatically purged (keeping only the last 2 days of logs in `/logs`).
- Beautiful, formatted Test Reports and Evidences (Berita Acara/BA) will be automatically generated inside the `/reports` directory in **PDF, DOCX, XLSX, and HTML** formats
