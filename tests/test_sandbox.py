import pytest
import copy
from utils.logger import get_logger
from helpers.evidence_collector import evidence_collector
from utils.generators import (
    generate_transaction_number, generate_ktp, today, 
    generate_tanggal_lahir, calculate_tanggal_akhir_asuransi, calculate_usia
)
from api.endpoints import SUBMIT_DRAFT_AKSEPTASI
from db.queries import QUERY_CEK_DRAFT_AKSEPTASI

logger = get_logger(__name__)

# ==============================================================================
# SANDBOX TESTING AREA
# ==============================================================================
# Gunakan file ini jika kamu ingin:
# 1. Membuat skenario baru yang sangat custom (misal tenor ganjil, umur limit, dsb).
# 2. Nge-hit API satu per satu secara manual untuk melihat kelakuannya sebelum
#    memasukkannya ke dalam payload_factory.py dan collections/test_script.xlsx.
#
# Perhatian: Sebaiknya TC di sini dipindahkan ke flow utama jika sudah stabil.
# ==============================================================================

def test_sandbox_experiment(api_client, db_client, base_payloads):
    tc_id = "TC-SANDBOX-01"
    
    evidence_collector.set_test_metadata(
        tc_id=tc_id,
        tc_name="Eksperimen Skenario Baru",
        expected_result="Sistem merespon dengan benar",
        precondition="Data payload di-setup manual via sandbox"
    )
    logger.info(f"Executing {tc_id} (Sandbox)...")

    # 2. Persiapan Data (Hardcode/Manual Setup)
    trx = generate_transaction_number()
    ktp = generate_ktp()
    tanggal_rencana_realisasi = today()
    tenor = 12
    tanggal_akhir_asuransi = calculate_tanggal_akhir_asuransi(tanggal_rencana_realisasi, tenor)
    tanggal_lahir = generate_tanggal_lahir(min_age=18, max_age=65, ref_date_str=tanggal_rencana_realisasi, tenor_months=tenor)
    usia = calculate_usia(tanggal_lahir, tanggal_rencana_realisasi)
    
    payload = copy.deepcopy(base_payloads.get("submit_draft", {}))
    payload["nomor_transaksi"] = trx
    payload["ktp"] = ktp
    payload["tanggal_rencana_realisasi"] = tanggal_rencana_realisasi
    payload["tanggal_akhir_asuransi"] = tanggal_akhir_asuransi
    payload["tanggal_lahir"] = tanggal_lahir
    payload["tenor"] = tenor
    payload["usia"] = usia
    
    # 3. Hit API
    resp = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload)
    
    # 4. Tambahkan Evidence & Assertion
    evidence_collector.add_api_evidence(tc_id, SUBMIT_DRAFT_AKSEPTASI, "POST", payload, resp.json() if resp.content else {}, resp.status_code)
    assert resp.status_code == 200, f"Error: {resp.text}"

    # Jika butuh validasi DB:
    db_res = db_client.execute_query(QUERY_CEK_DRAFT_AKSEPTASI, (trx,))
    evidence_collector.add_db_evidence(tc_id, f"Validasi DB", db_res)

    evidence_collector.set_test_status(tc_id, "Passed")
