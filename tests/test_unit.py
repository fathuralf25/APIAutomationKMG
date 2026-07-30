import pytest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils.generators import generate_tanggal_lahir, calculate_tanggal_akhir_asuransi, calculate_usia
from utils.generators import generate_transaction_number, generate_ktp, generate_loan_number

def test_generate_transaction_number():
    trx = generate_transaction_number()
    assert trx.startswith("AKS-")
    assert len(trx.split("-")) >= 3
    # Check format AKS-YYYYMMDD-HHMMSS-XXXX
    parts = trx.split("-")
    assert len(parts[1]) == 8 # YYYYMMDD
    assert len(parts[2]) == 6 # HHMMSS

def test_generate_ktp():
    ktp = generate_ktp()
    assert len(ktp) == 16
    assert ktp.isdigit()

def test_calculate_tanggal_akhir_asuransi():
    # 120 months = 10 years
    akhir = calculate_tanggal_akhir_asuransi("2026-04-10", 120)
    assert akhir == "2036-04-10"

def test_generate_tanggal_lahir():
    # Realization: 2026-04-10, Tenor: 120 months (10 years) -> Akhir Asuransi: 2036-04-10
    # Min age: 18 at 2026-04-10
    # Max age: 65 at 2036-04-10
    tanggal_lahir = generate_tanggal_lahir(min_age=18, max_age=65, ref_date_str="2026-04-10", tenor_months=120)
    
    # Calculate age at realization
    usia_realisasi = calculate_usia(tanggal_lahir, "2026-04-10")
    assert usia_realisasi >= 18, f"Age at realization should be >= 18, got {usia_realisasi} for birthdate {tanggal_lahir}"
    
    # Calculate age at akhir asuransi
    usia_akhir = calculate_usia(tanggal_lahir, "2036-04-10")
    assert usia_akhir <= 65, f"Age at end of insurance should be <= 65, got {usia_akhir} for birthdate {tanggal_lahir}"
    
def test_calculate_usia():
    # Born 2000-01-01, Target 2020-01-01 -> 20
    age1 = calculate_usia("2000-01-01", "2020-01-01")
    assert age1 == 20
    
    # Born 2000-01-02, Target 2020-01-01 -> 19
    age2 = calculate_usia("2000-01-02", "2020-01-01")
    assert age2 == 19
