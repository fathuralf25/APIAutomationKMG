from datetime import datetime
import math

def calculate_restitusi_expected(tanggal_mulai_covering: str, tanggal_restitusi: str, jangka_waktu_bulan: int, premi: float) -> float:
    """
    Calculate the expected restitution value based on business rules.
    If days <= 30, full refund.
    If days > 30, proportional refund.
    """
    fmt = "%Y-%m-%d"
    t_mulai = datetime.strptime(tanggal_mulai_covering, fmt)
    t_restitusi = datetime.strptime(tanggal_restitusi, fmt)
    
    days_passed = (t_restitusi - t_mulai).days
    
    if days_passed <= 30:
        return round(premi, 2)
    else:
        N = jangka_waktu_bulan
        # Assuming T is calculated as (days_passed - 1) // 30, or simply based on boundary.
        # Since we use exactly +31 days for > 30 days scenario, T will be 1.
        T = math.floor((days_passed - 1) / 30) if days_passed > 30 else 0
        if T == 0 and days_passed > 30: 
            T = 1
            
        premi_nett = ((N - T) / N) * (0.35 * (premi * 0.90))
        return round(premi_nett, 2)
