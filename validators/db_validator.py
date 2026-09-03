import time
from db.queries import QUERY_CEK_DRAFT_AKSEPTASI, QUERY_CEK_TERBIT_POLIS

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

def validate_terbit_polis(db_client, trx_id: str, tc_id: str, evidence_collector, max_retries: int = 10, tahap_name: str = ""):
    """
    Validates polis terbit in DB with retries, and adds evidence.
    """
    db_result = None
    for _ in range(max_retries):
        db_result = db_client.execute_query(QUERY_CEK_TERBIT_POLIS, (trx_id,))
        if db_result and len(db_result) > 0 and isinstance(db_result[0], dict) and db_result[0].get("no_sertifikat"):
            break
        time.sleep(2)
        
    evidence_name = f"{QUERY_CEK_TERBIT_POLIS} ({tahap_name})" if tahap_name else QUERY_CEK_TERBIT_POLIS
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_result)
    return db_result

from db.queries import QUERY_GET_RESTITUSI

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
                
    evidence_name = f"QUERY_GET_RESTITUSI ({tahap_name})" if tahap_name else "QUERY_GET_RESTITUSI"
    evidence_collector.add_db_evidence(tc_id, evidence_name, db_res)
    return db_res
