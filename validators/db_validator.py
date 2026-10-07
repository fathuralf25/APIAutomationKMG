import time
from db.queries import QUERY_FINAL_STATUS_RESTITUSI, QUERY_CEK_JURNAL_BK_RESTITUSI, QUERY_CEK_DRAFT_AKSEPTASI, QUERY_CEK_TERBIT_POLIS, QUERY_GET_RESTITUSI, QUERY_GET_SERTIFIKAT_DTL_ENDORSEMENT, QUERY_VALIDASI_PEMBAYARAN_RESTITUSI

def validate_draft_akseptasi(db_client, trx_id: str, tc_id: str, evidence_collector, tahap_name: str = ""):
    """
    Validates draft akseptasi in DB and adds evidence.
    """
    db_res = db_client.execute_query(QUERY_CEK_DRAFT_AKSEPTASI, (trx_id,))
    if db_res:
        for row in db_res:
            row["Validasi DB"] = f"Status {tahap_name}" if tahap_name else "Data Ditemukan"
            row["Response API"] = "Success"
            
    evidence_name = f"{QUERY_CEK_DRAFT_AKSEPTASI} ({tahap_name})" if tahap_name else QUERY_CEK_DRAFT_AKSEPTASI
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_res)
    return db_res

def validate_terbit_polis(db_client, trx_id: str, tc_id: str, evidence_collector, max_retries: int = 30, tahap_name: str = ""):
    """
    Validates polis terbit in DB with retries, and adds evidence.
    """
    db_result = None
    for _ in range(max_retries):
        db_result = db_client.execute_query(QUERY_CEK_TERBIT_POLIS, (trx_id,))
        if db_result and len(db_result) > 0 and isinstance(db_result[0], dict) and db_result[0].get("no_sertifikat") and str(db_result[0].get("status_akseptasi")) == "9":
            break
        time.sleep(2)
        
    evidence_name = f"{QUERY_CEK_TERBIT_POLIS} ({tahap_name})" if tahap_name else QUERY_CEK_TERBIT_POLIS
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_result)
    return db_result

def validate_restitusi(db_client, trx_id: str, tc_id: str, evidence_collector, expected_status: str = None, tahap_name: str = ""):
    """
    Validates restitution (refund) in DB and adds evidence.
    expected_status can be 'AGREED', 'COUNTER' based on nominal_disetujui logic.
    """
    db_res = db_client.execute_query(QUERY_GET_RESTITUSI, (trx_id,))
    
    if db_res:
        for row in db_res:
            row["Validasi DB"] = f"Status {tahap_name}" if tahap_name else "Data Ditemukan"
            # Optional business logic validation:
            if expected_status == "AGREED":
                assert row.get("nominal_disetujui") is not None, "nominal_disetujui seharusnya TERISI (AGREED)"
            elif expected_status == "COUNTER":
                assert row.get("nominal_disetujui") is None, "nominal_disetujui seharusnya KOSONG (COUNTER)"
            elif expected_status == "SANGGAHAN":
                assert row.get("status_akseptasi") == "13", f"Status akseptasi seharusnya 13 (Sanggahan/Proses), tapi dapat {row.get('status_akseptasi')}"
                assert row.get("nominal_disetujui") is None, "nominal_disetujui seharusnya KOSONG (Masih disanggah)"
                
    evidence_name = f"QUERY_GET_RESTITUSI ({tahap_name})" if tahap_name else "QUERY_GET_RESTITUSI"
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_res)
    return db_res

def validate_sertifikat_dtl(db_client, policy_no_prev: str, tc_id: str, evidence_collector, tahap_name: str = ""):
    """
    Validates certificate detail (endorsement) in DB and adds evidence.
    """
    db_res = db_client.execute_query(QUERY_GET_SERTIFIKAT_DTL_ENDORSEMENT, (policy_no_prev,))
    
    if db_res:
        for row in db_res:
            row["Validasi DB"] = f"Endorsement {tahap_name}" if tahap_name else "Endorsement Ditemukan"
            
    evidence_name = f"QUERY_GET_SERTIFIKAT_DTL ({tahap_name})" if tahap_name else "QUERY_GET_SERTIFIKAT_DTL"
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_res)
    return db_res

def validate_pembayaran_restitusi(db_client, nomor_loan: str, tc_id: str, evidence_collector, tahap_name: str = ""):
    """
    Validates pembayaran restitusi detail in DB based on nomor_loan and adds evidence.
    """
    db_res = db_client.execute_query(QUERY_VALIDASI_PEMBAYARAN_RESTITUSI, (nomor_loan,))
    
    if db_res:
        for row in db_res:
            row["Validasi DB"] = f"Validasi Pembayaran {tahap_name}" if tahap_name else "Validasi Pembayaran Restitusi"
            
    evidence_name = f"QUERY_VALIDASI_PEMBAYARAN_RESTITUSI ({tahap_name})" if tahap_name else "QUERY_VALIDASI_PEMBAYARAN_RESTITUSI"
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_res)
    return db_res


def validate_jurnal_bk_restitusi(db_client, nomor_transaksi: str, tc_id: str, evidence_collector, tahap_name: str = ""):
    """
    Validates Jurnal BK for restitusi in DB based on nomor_transaksi and adds evidence.
    """
    db_res = db_client.execute_query(QUERY_CEK_JURNAL_BK_RESTITUSI, (nomor_transaksi,))
    
    if db_res:
        for row in db_res:
            row["Validasi DB"] = f"Validasi Jurnal BK {tahap_name}" if tahap_name else "Validasi Jurnal BK Restitusi"
            
    evidence_name = f"QUERY_CEK_JURNAL_BK ({tahap_name})" if tahap_name else "QUERY_CEK_JURNAL_BK"
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_res)
    return db_res

def validate_final_status_restitusi(db_client, trx_id: str, tc_id: str, evidence_collector):
    """
    Validates final restitution status in DB (status_proses_restitusi = 6, and no_jurnal exists).
    """
    db_res = db_client.execute_query(QUERY_FINAL_STATUS_RESTITUSI, (trx_id,))
    if db_res and len(db_res) > 0:
        row = db_res[0]
        # Pastikan tidak None sebelum membandingkan
        status_restitusi = str(row.get("status_proses_restitusi", ""))
        
        # Validasi Jurnal dan Status 6
        if status_restitusi == "6" and row.get("no_jurnal"):
            row["Validasi Akhir"] = "Status Proses Restitusi = 6 (Selesai) & Jurnal Terbentuk"
        else:
            row["Validasi Akhir"] = f"Warning: Status Restitusi = {status_restitusi}, Jurnal = {row.get('no_jurnal')}"
            
        evidence_collector.add_db_evidence(tc_id, "Final Status Restitusi (Validasi Jurnal)", [row])
        return row
    return None
