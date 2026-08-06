# API Automation Project Rules

## Project

Python API Automation Framework

## Tech Stack

- Python
- pytest
- requests
- PostgreSQL
- python-dotenv

---

# General Rules

- Do not rename existing folders.
- Do not create unnecessary folders.
- Reuse existing helper functions.
- Never hardcode URLs.
- Always read configuration from .env.
- Keep functions small and reusable.
- Do not duplicate code.

---

# Folder Structure

api/
config/
db/
payloads/
scripts/
tests/
utils/

Keep this structure.

---

# Payload

Payload JSON inside payloads/ is TEMPLATE ONLY.

Never assume payload values are final.

Dynamic fields must be generated before sending request.

---

# Dynamic Fields

Generate dynamically when needed:

- nomor_transaksi
- ktp
- tanggal_rencana_realisasi
- tanggal_akhir_asuransi
- tanggal_lahir
- tenor
- nomor_loan
- nomor_perjanjian_kredit
- nomor_reff_pembayaran

---

# Business Rules

## Submit Draft Akseptasi

nomor_transaksi format

AKS-YYYYMMDD-HHMMSS

ktp

16 numeric digits

## KTP Business Rules

A customer (identified by KTP) can only have ONE active insurance submission at a time.

Rule:

- A KTP cannot create another Submit Draft Akseptasi if there is an existing active submission.
- This restriction applies from Draft until Policy Issued.
- A new submission using the same KTP is only allowed when the previous submission has been cancelled.
- Before generating a new test case using an existing KTP, the framework must validate the latest application status from PostgreSQL.
- Only when the latest status is 11 (Cancelled) may the same KTP be reused.

Implementation Rules:

- Always check database status before deciding whether to reuse or generate a KTP.
- Database validation is mandatory before Submit Draft when KTP reuse is possible.

tanggal_akhir_asuransi

=

tanggal_rencana_realisasi + tenor

Age

Minimum:
18 years + 1 day

Maximum:
65 years (Age at tanggal_akhir_asuransi must not exceed 65 years. Therefore, Usia Debitur at tanggal_rencana_realisasi + Tenor in years <= 65)

Tenor:
Can now be greater than 60 months (5 years) as long as the max age rule is satisfied.

---

## Inquiry Loan

nomor_transaksi

comes from previous Submit Draft

nomor_loan

must be unique

nomor_perjanjian_kredit

must be unique

tanggal_akad

must not be later than tanggal_rencana_realisasi

outstanding

must not exceed uang_pertanggungan

---

## Otorisasi Penyelia

Use:

- nomor_transaksi from previous flow
- nomor_loan from previous flow

---

## Pembayaran Premi

Use:

nomor_loan

from previous flow

nomor_reff_pembayaran

must be unique

nominal_pembayaran

must equal premi returned by Submit Draft

---

## Pembatalan

Use:

nomor_transaksi

from previous flow

Cancellation only valid when status akseptasi = 9

---

# Database

Database:

PostgreSQL

Every successful API should support database validation whenever applicable.

---

# Coding Style

Prefer reusable helper functions.

Keep business rules separate from API request logic.

Keep test files easy to read.

Avoid hardcoded values.
All import and from statements must be placed at the top of the file, not inside functions or methods (DRY principle).

---

# Testing

Implement one business flow at a time.

Do not generate tests for all endpoints at once.

Always preserve data relationship between endpoints.

## Execution Policy

Never execute Python scripts, pytest, or shell commands unless explicitly approved by the user.

Setiap ada perubahan kode atau sebelum mengeksekusi sesuatu, WAJIB memberikan rencana implementasi (Implementation Plan) terlebih dahulu agar bisa didiskusikan.

Wait for approval and discussion before running any command or making any changes.

## Project Vision

This repository is not only an API Automation Framework.

The final goal is to become an Enterprise QA Automation Platform.

Features include:

- API Automation
- PostgreSQL Validation
- Business Flow Automation
- Evidence Collection
- HTML Reporting
- Excel Reporting
- BA SIT Generator
- BA UAT Generator
- Company document automation

## Reporting & Test Steps Rules

- When defining or generating "Test Steps" (Langkah Pengujian), **NEVER** include the word "hasil" (result).
- Any description regarding the "hasil" (outcome) must exclusively be placed in the "Expected Result" or "Actual Result" sections, never in the Test Steps.

## Payload Rules

Payload JSON files are templates only.

Do not hardcode dynamic business values.

All dynamic values must be injected through reusable helper functions.

Test files must never manually generate business values.

Business values must be generated through dedicated generator modules.

## File Handling Rules

- Never use absolute paths outside the project workspace like `C://downloads/`.
- When a file is uploaded by the user, read it directly from the workspace folder, save it locally in the project directory, and extract/process it directly from there.
