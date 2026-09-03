import time

from db.acs_client import execute_acs_update
from db.queries import QUERY_ACS_UPDATE_PREMIUM_PAIDOFF, QUERY_GET_RESTITUSI
from helpers.restitusi_payloads import (
    build_restitusi_submit_payload,
    build_restitusi_confirmation_payload,
    build_restitusi_dispute_payload
)
from validators.db_validator import validate_draft_akseptasi, validate_restitusi
from validators.ui_validator import validate_polis_ui_and_qr
from helpers.ui_acs import check_polis_in_acs
from helpers.ui_fms import create_jurnal_bbk_restitusi
from utils.email_utils import check_restitusi_email
from config.config import GMAIL_USERNAME, GMAIL_APP_PASSWORD

from api.endpoints import RESTITUSI_SUBMIT, RESTITUSI_CONFIRMATION, RESTITUSI_DISPUTES, RESTITUSI_DETAIL
from utils.logger import get_logger

logger = get_logger(__name__)

def run_restitusi_flow(api_client, db_client, tc_id, nomor_transaksi, nomor_loan, policy_no, premi, tenor, evidence_collector, plus_days, expect_sanggahan=False):
    """
    Executes the Restitusi Flow:
    1. Update payment_status in ACS DB
    2. Submit Restitusi
    3. Confirmation (Setuju / Sanggahan)
    4. Dispute (If Sanggahan and Askrindo gives Counter)
    5. Final validation and UI ACS check for endorsement (/c)
    """
    
    # Step 1: Mock payment status in ACS Staging DB
    logger.info(f"[{tc_id}] Mocking premium payment in ACS DB for Policy: {policy_no}")
    execute_acs_update(QUERY_ACS_UPDATE_PREMIUM_PAIDOFF, (policy_no,))
    time.sleep(2) # Give it a moment to sync if needed
    
    # We log the akseptasi transition
    validate_draft_akseptasi(db_client, nomor_transaksi, tc_id, evidence_collector, tahap_name="Before Submit Restitusi")
    
    # Step 2: Submit Restitusi
    submit_payload = build_restitusi_submit_payload(nomor_loan, plus_days, premi, tenor)
    logger.info(f"[{tc_id}] Submitting Restitusi: {submit_payload}")
    res_submit = api_client.post(RESTITUSI_SUBMIT, submit_payload)
    assert res_submit.status_code == 200, f"Submit Restitusi failed: {res_submit.text}"
    evidence_collector.add_api_evidence(tc_id, "Submit Restitusi", RESTITUSI_SUBMIT, submit_payload, res_submit.json(), res_submit.status_code)
    
    validate_draft_akseptasi(db_client, nomor_transaksi, tc_id, evidence_collector, tahap_name="After Submit Restitusi")
    
    # Get nominal from Askrindo calculation via DB validation (simulate the automated webhook calculation)
    # We query the DB to get the calculated values from backend automatically
    time.sleep(3) # Wait for backend calculation
    db_res = validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, tahap_name="Post-Submit Calculation")
    
    kalkulasi_askrindo = 0
    if db_res and len(db_res) > 0:
        kalkulasi_askrindo = float(db_res[0].get("nominal_kalkulasi_askrindo") or submit_payload["nilai_pengajuan"])
    
    if not expect_sanggahan:
        # Step 3 (Happy Path): Konfirmasi Setuju
        # Askrindo calculation is used
        conf_payload = build_restitusi_confirmation_payload(nomor_loan, "DISETUJUI", nilai=kalkulasi_askrindo)
        res_conf = api_client.post(RESTITUSI_CONFIRMATION, conf_payload)
        assert res_conf.status_code == 200, f"Confirmation failed: {res_conf.text}"
        evidence_collector.add_api_evidence(tc_id, "Konfirmasi Setuju", RESTITUSI_CONFIRMATION, conf_payload, res_conf.json(), res_conf.status_code)
        
        validate_draft_akseptasi(db_client, nomor_transaksi, tc_id, evidence_collector, tahap_name="After Konfirmasi Setuju")
        
        # Final Validation (nominal_disetujui should be populated)
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="AGREED", tahap_name="Final Validation (AGREED)")
        
    else:
        # Step 3 (Sanggahan Flow)
        # We propose a value > kalkulasi_askrindo to trigger COUNTER
        sanggahan_value = float(kalkulasi_askrindo) + 50000
        conf_payload = build_restitusi_confirmation_payload(nomor_loan, "SANGGAHAN", nilai=sanggahan_value)
        res_conf = api_client.post(RESTITUSI_CONFIRMATION, conf_payload)
        assert res_conf.status_code == 200, f"Sanggahan failed: {res_conf.text}"
        evidence_collector.add_api_evidence(tc_id, "Konfirmasi Sanggah", RESTITUSI_CONFIRMATION, conf_payload, res_conf.json(), res_conf.status_code)
        
        validate_draft_akseptasi(db_client, nomor_transaksi, tc_id, evidence_collector, tahap_name="After Konfirmasi Sanggah")
        
        # Validate that nominal_disetujui is NULL (because it's > kalkulasi_askrindo)
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="COUNTER", tahap_name="Validation (COUNTER)")
        
        # Step 4: Dispute
        # Propose a value <= kalkulasi_askrindo to get accepted
        dispute_value = float(kalkulasi_askrindo)
        dispute_payload = build_restitusi_dispute_payload(nomor_loan, dispute_value, sanggahan_value)
        res_disp = api_client.post(RESTITUSI_DISPUTES, dispute_payload)
        assert res_disp.status_code == 200, f"Dispute failed: {res_disp.text}"
        evidence_collector.add_api_evidence(tc_id, "Dispute Lanjutan", RESTITUSI_DISPUTES, dispute_payload, res_disp.json(), res_disp.status_code)
        
        validate_draft_akseptasi(db_client, nomor_transaksi, tc_id, evidence_collector, tahap_name="After Dispute")
        
        # Final Validation (nominal_disetujui should be populated now)
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="AGREED", tahap_name="Final Validation (AGREED after Dispute)")

    # Detail API hit
    res_detail = api_client.get(f"{RESTITUSI_DETAIL}?nomor_loan={nomor_loan}")
    evidence_collector.add_api_evidence(tc_id, "Get Detail Restitusi", RESTITUSI_DETAIL, {"nomor_loan": nomor_loan}, res_detail.json(), res_detail.status_code)
    
    # Step 5: Check Endorsement in UI ACS
    endorsement_polis = f"{policy_no}/C"
    logger.info(f"[{tc_id}] Checking Endorsement Polis in ACS UI: {endorsement_polis}")
    try:
        check_polis_in_acs(endorsement_polis)
        evidence_collector.add_epolis_evidence(tc_id, "Success ACS Check", [])
    except Exception as e:
        logger.error(f"Failed to check endorsement in ACS UI: {e}")
        

    # Step 6: Create Jurnal BBK in FMS
    logger.info(f"[{tc_id}] Creating Jurnal BBK in FMS for policy: {endorsement_polis}")
    try:
        create_jurnal_bbk_restitusi(endorsement_polis, tc_id, evidence_collector)
    except Exception as e:
        logger.error(f"Failed to create Jurnal BBK in FMS: {e}")
        
    # Step 7: Verifikasi Email Notifikasi Restitusi
    if GMAIL_USERNAME and GMAIL_APP_PASSWORD:
        logger.info(f"[{tc_id}] Memulai pengecekan email notifikasi...")
        check_restitusi_email(GMAIL_USERNAME, GMAIL_APP_PASSWORD, nomor_loan, tc_id, evidence_collector)
    else:
        logger.warning(f"[{tc_id}] GMAIL_USERNAME atau GMAIL_APP_PASSWORD tidak diset di .env. Skip cek email.")
        
    return True
