from copy import deepcopy
from utils.generators import generate_transaction_number, generate_ktp, generate_loan_number, generate_perjanjian_kredit, generate_reff_pembayaran
from utils.generators import today, calculate_tanggal_akhir_asuransi, generate_tanggal_lahir
from datetime import datetime, timedelta

def build_dynamic_payload(tc_id: str, api_group: str, state: dict, base_payloads: dict) -> dict:
    """
    Builds the payload dynamically based on API Group and Test Case ID.
    """
    api_group = api_group.lower()

    if "a1" in api_group or "kalkulasi" in api_group:
        payload = deepcopy(base_payloads.get("kalkulator", {}))
        payload["ktp"] = generate_ktp()
        tanggal_rencana = today()
        tenor = 120
        
        if tc_id == "TC-37":
            tenor = 180
            payload["uang_pertanggungan"] = 100000000
            
        payload["tanggal_rencana_realisasi"] = tanggal_rencana
        payload["tenor"] = tenor
        payload["tanggal_lahir"] = generate_tanggal_lahir(18, 65, tanggal_rencana, tenor)
        
        state["kalkulator_payload"] = payload
        return payload

    elif "a4" in api_group or "inquiry" in api_group:
        payload = deepcopy(base_payloads.get("inquiry", {}))
        payload["nomor_transaksi"] = state.get("last_success_trx", "TRX-MOCK")
        payload["nomor_loan"] = generate_loan_number()
        payload["nomor_perjanjian_kredit"] = generate_perjanjian_kredit()
        payload["tanggal_akad"] = today()
        payload["outstanding"] = state.get("last_success_up", 50000000)
        
        if tc_id == "TC-7":
            payload["nomor_transaksi"] = "TRX-INVALID"
        elif tc_id == "TC-22":
            d = datetime.strptime(today(), "%Y-%m-%d")
            payload["tanggal_akad"] = (d + timedelta(days=1)).strftime("%Y-%m-%d")
            
        if tc_id in ["TC-6", "TC-29", "TC-31", "TC-32"]:
            state["last_success_loan"] = payload["nomor_loan"]
            
        return payload

    elif "a5" in api_group or "otorisasi" in api_group:
        payload = deepcopy(base_payloads.get("otorisasi", {}))
        payload["nomor_transaksi"] = state.get("last_success_trx", "TRX-MOCK")
        payload["nomor_loan"] = state.get("last_success_loan", "LN-MOCK")
        
        if tc_id == "TC-8":
            payload["status"] = "DISETUJUI"
        elif tc_id == "TC-9":
            payload["status"] = "DITOLAK"
            
        return payload

    elif "a6" in api_group or "pembayaran" in api_group:
        payload = deepcopy(base_payloads.get("payment", {}))
        payload["nomor_loan"] = state.get("last_success_loan", "LN-MOCK")
        payload["nomor_reff_pembayaran"] = generate_reff_pembayaran()
        
        expected_premi = state.get("last_premi", 2890000.0)
        payload["nominal_pembayaran"] = expected_premi
        
        if tc_id == "TC-11":
            payload["nominal_pembayaran"] = expected_premi + 1000
            
        return payload

    elif "a7" in api_group or "pembatalan" in api_group:
        payload = deepcopy(base_payloads.get("pembatalan", {}))
        # Default for pembatalan
        payload["nomor_transaksi"] = state.get("draft_for_cancel", "TRX-MOCK")
        
        if tc_id == "TC-13":
            # Batal pada polis issued
            payload["nomor_transaksi"] = state.get("last_success_trx", "TRX-MOCK")
        elif tc_id == "TC-14":
            payload["nomor_transaksi"] = "TRX-INVALID"
        return payload

    else:
        # Default to SUBMIT_DRAFT_AKSEPTASI (A2)
        payload = deepcopy(base_payloads.get("submit_draft", {}))
        
        # Default valid values
        tanggal_rencana = today()
        tenor = 12
        tanggal_akhir = calculate_tanggal_akhir_asuransi(tanggal_rencana, tenor)
        # Generate normal age of 27 to avoid any age boundary validations for normal TCs
        dt_rencana = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
        normal_tanggal_lahir = (dt_rencana.replace(year=dt_rencana.year - 27)).strftime("%Y-%m-%d")
        nomor_transaksi = generate_transaction_number()
        
        payload["nomor_transaksi"] = nomor_transaksi
        payload["tanggal_rencana_realisasi"] = tanggal_rencana
        payload["tanggal_akhir_asuransi"] = tanggal_akhir
        payload["tenor"] = tenor
        payload["ktp"] = generate_ktp()
        payload["tanggal_lahir"] = normal_tanggal_lahir
        payload["uang_pertanggungan"] = 50000000
        payload["usia"] = 27
        
        # Specific Negative Modifications
        if tc_id == "TC-2":
            payload["uang_pertanggungan"] = 0
        elif tc_id == "TC-3":
            payload["kode_bank"] = "INVALID_BANK"
        elif tc_id == "TC-15":
            payload["usia"] = "ABC" # invalid type
        elif tc_id == "TC-16":
            payload["tenor"] = 9999 # invalid tenor
        elif tc_id == "TC-17":
            payload["kode_pos"] = "ABCDE"
        elif tc_id == "TC-18" or tc_id == "TC-26":
            # Usia + Tenor > 65 (Must be rejected)
            d = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
            # Set usia to exactly 65 right now. Adding any tenor will make it > 65
            payload["tanggal_lahir"] = (d.replace(year=d.year - 65)).strftime("%Y-%m-%d")
            payload["tenor"] = 120
        elif tc_id == "TC-19":
            # Realisasi lebih besar dari Akhir Asuransi (Backdated invalid)
            payload["tanggal_rencana_realisasi"] = today()
            # Akhir asuransi backdated 1 tahun dari hari ini
            d = datetime.strptime(today(), "%Y-%m-%d")
            payload["tanggal_akhir_asuransi"] = (d.replace(year=d.year - 1)).strftime("%Y-%m-%d")
            payload["tanggal_lahir"] = generate_tanggal_lahir(18, 65, payload["tanggal_rencana_realisasi"], 12)
        elif tc_id == "TC-20":
            payload["kode_cabang"] = "INVALID"
        elif tc_id == "TC-21":
            if "ktp" in payload:
                del payload["ktp"] # missing mandatory
        elif tc_id == "TC-23":
            payload["ktp"] = state.get("active_ktp", payload["ktp"])
        elif tc_id == "TC-28":
            payload["ktp"] = state.get("ktp_for_cancel", payload["ktp"])
        elif tc_id == "TC-24":
            # Usia < 18
            payload["tanggal_lahir"] = generate_tanggal_lahir(17, 17, tanggal_rencana, 12)
        elif tc_id == "TC-25":
            # Exactly 18 years
            d = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
            payload["tanggal_lahir"] = (d.replace(year=d.year - 18)).strftime("%Y-%m-%d")
        elif tc_id == "TC-27":
            # Usia is wrong param, but calc is valid
            payload["usia"] = 99 
            payload["tanggal_lahir"] = generate_tanggal_lahir(64, 64, tanggal_rencana, 12)
        elif tc_id == "TC-31":
            # Usia 20 thn, tenor 180 bulan (15 thn)
            payload["tenor"] = 180
            payload["tanggal_akhir_asuransi"] = calculate_tanggal_akhir_asuransi(tanggal_rencana, 180)
            d = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
            payload["tanggal_lahir"] = (d.replace(year=d.year - 20)).strftime("%Y-%m-%d")
            payload["usia"] = 20
        elif tc_id == "TC-32":
            # Usia 50 thn, tenor 180 bulan (15 thn). Usia akhir = 65 thn persis
            payload["tenor"] = 180
            payload["tanggal_akhir_asuransi"] = calculate_tanggal_akhir_asuransi(tanggal_rencana, 180)
            d = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
            payload["tanggal_lahir"] = (d.replace(year=d.year - 50)).strftime("%Y-%m-%d")
            payload["usia"] = 50
        elif tc_id == "TC-33":
            # Tenor 72 bulan (6 thn), boundary value: usia akhir 65 thn + 1 hari
            payload["tenor"] = 72
            payload["tanggal_akhir_asuransi"] = calculate_tanggal_akhir_asuransi(tanggal_rencana, 72)
            d = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
            # 59 years and 1 day ago
            dt_lahir = d.replace(year=d.year - 59) - timedelta(days=1)
            payload["tanggal_lahir"] = dt_lahir.strftime("%Y-%m-%d")
            payload["usia"] = 59
        elif tc_id == "TC-34":
            # Usia 55 thn, tenor 180 bulan (15 thn). Usia akhir = 70 thn (>65)
            payload["tenor"] = 180
            payload["tanggal_akhir_asuransi"] = calculate_tanggal_akhir_asuransi(tanggal_rencana, 180)
            d = datetime.strptime(tanggal_rencana, "%Y-%m-%d")
            payload["tanggal_lahir"] = (d.replace(year=d.year - 55)).strftime("%Y-%m-%d")
            payload["usia"] = 55
        elif tc_id == "TC-35":
            # Tenor 120 bulan (10 thn) tapi akhir asuransi diset +5 thn
            payload["tenor"] = 120
            payload["tanggal_akhir_asuransi"] = calculate_tanggal_akhir_asuransi(tanggal_rencana, 60) # +5 years
        elif tc_id == "TC-36":
            # Tenor 24 bulan (2 thn) tapi akhir asuransi diset +10 thn
            payload["tenor"] = 24
            payload["tanggal_akhir_asuransi"] = calculate_tanggal_akhir_asuransi(tanggal_rencana, 120) # +10 years

        if tc_id in ["TC-1", "TC-4"]:
            # Success Case, save state
            if tc_id == "TC-1":
                # Draft khusus untuk dibatalkan di TC-12
                state["draft_for_cancel"] = payload["nomor_transaksi"]
                state["ktp_for_cancel"] = payload["ktp"]
            elif tc_id == "TC-4":
                # Draft untuk di-inquiry dan dibayar sampai Polis
                state["last_success_trx"] = payload["nomor_transaksi"]
                state["last_success_up"] = payload["uang_pertanggungan"]
                state["last_success_ktp"] = payload["ktp"]
                # Save active KTP for negative test TC-23
                state["active_ktp"] = payload["ktp"]
            
        return payload
