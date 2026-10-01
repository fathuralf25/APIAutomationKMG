from utils.logger import get_logger
from helpers.qr_scanner import download_and_scan_policy_qr
from helpers.ui_acs import check_polis_in_acs

logger = get_logger(__name__)

def validate_polis_ui_and_qr(tc_id, no_sertifikat, url_download, trx_id, data_submit, db_result, evidence_collector):
    """
    Validates QR code scanning and ACS UI screenshot, then calculates premium validation.
    """
    if not no_sertifikat:
        return

    # QR Scan
    qr_result, image_paths = download_and_scan_policy_qr(no_sertifikat, url_download, trx_id)
    evidence_collector.add_epolis_evidence(tc_id, qr_result, image_paths)
    
    # Premium extraction
    api_premi = float(data_submit.get("data", {}).get("premi", 0.0))
    db_premi = 0.0
    if db_result and isinstance(db_result, list) and len(db_result) > 0 and isinstance(db_result[0], dict):
        db_premi = float(db_result[0].get('premi', 0.0))
        
    premi_acs = 0.0
    
    # UI ACS Check
    try:
        from db.acs_client import wait_for_policy_in_acs, execute_acs_update
        from db.queries import QUERY_ACS_UPDATE_PREMIUM_PAIDOFF
        
        logger.info(f"[{tc_id}] Menunggu sinkronisasi polis {no_sertifikat} ke ACS DB...")
        if wait_for_policy_in_acs(no_sertifikat, max_retries=60, delay_sec=10):
            logger.info(f"[{tc_id}] Patching status pembayaran menjadi Lunas (1) di ACS DB...")
            execute_acs_update(QUERY_ACS_UPDATE_PREMIUM_PAIDOFF, (no_sertifikat,))
            
        ui_res = check_polis_in_acs(no_sertifikat)
        screenshot_paths = ui_res.get("paths", [])
        premi_acs = ui_res.get("premi_acs", 0.0)
        
        for path in screenshot_paths:
            sys_name = "FMS" if "fms_jurnal" in path else "ACS"
            evidence_collector.add_ui_evidence(tc_id, sys_name, path)
    except Exception as e:
        logger.error(f"Failed to check polis in ACS for {no_sertifikat}: {e}")
    finally:
        evidence_collector.evidences[tc_id]["premi_validation"] = {
            "api": api_premi,
            "db": db_premi,
            "acs": premi_acs,
            "status": "Passed" if api_premi == db_premi == premi_acs and api_premi > 0 else "Failed"
        }
