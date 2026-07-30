import random
import string
from datetime import datetime
from dateutil.relativedelta import relativedelta

def random_number(length: int) -> str:
    return ''.join(random.choices(string.digits, k=length))

def random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_uppercase, k=length))

def generate_transaction_number() -> str:
    """
    Generate a unique transaction number formatted as AKS-YYYYMMDD-HHMMSS-XXXX.
    """
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    random_suffix = random_string(6)
    return f"AKS-{timestamp}-{random_suffix}"

def generate_ktp() -> str:
    """Generate a 16-digit KTP number."""
    return random_number(16)

def generate_npwp() -> str:
    """Generate a 15-digit NPWP number."""
    return random_number(15)

def generate_loan_number() -> str:
    """Generate a unique loan number."""
    return f"LN-{random_number(6)}"

def generate_perjanjian_kredit() -> str:
    """Generate a unique perjanjian kredit number."""
    year_prefix = datetime.now().strftime('%y')
    return f"{year_prefix}PK{random_number(6)}"

def generate_reff_pembayaran() -> str:
    """Generate a unique reference number for premium payment."""
    return f"REF-PAY-{random_number(8)}"

def today() -> str:
    """Returns today's date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

def calculate_tanggal_akhir_asuransi(tanggal_rencana: str, tenor_months: int) -> str:
    """Calculate the end date of insurance based on the realization date and tenor."""
    dt_rencana = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
    dt_akhir = dt_rencana + relativedelta(months=tenor_months)
    return dt_akhir.strftime("%Y-%m-%d")

def generate_tanggal_lahir(min_age: int = 18, max_age: int = 65, ref_date_str: str = None, tenor_months: int = 0) -> str:
    """Generate a random birth date that satisfies the age requirements."""
    if ref_date_str:
        ref_date = datetime.strptime(ref_date_str, "%Y-%m-%d")
    else:
        ref_date = datetime.now()
        
    akhir_asuransi = ref_date + relativedelta(months=tenor_months)
    max_birth_date = ref_date - relativedelta(years=min_age) - relativedelta(days=1)
    min_birth_date = akhir_asuransi - relativedelta(years=max_age) + relativedelta(days=1)
    
    return max_birth_date.strftime("%Y-%m-%d")

def calculate_usia(tanggal_lahir: str, reference_date: str) -> int:
    """Calculate age exactly as required by Askrindo business rule."""
    dt_lahir = datetime.strptime(tanggal_lahir, "%Y-%m-%d")
    dt_ref = datetime.strptime(reference_date, "%Y-%m-%d")
    return dt_ref.year - dt_lahir.year - ((dt_ref.month, dt_ref.day) < (dt_lahir.month, dt_lahir.day))
