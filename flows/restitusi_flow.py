import time

from db.acs_client import execute_acs_update
from db.queries import QUERY_GET_SERTIFIKAT_DTL_ENDORSEMENT, QUERY_ACS_UPDATE_PREMIUM_PAIDOFF, QUERY_GET_RESTITUSI
from helpers.restitusi_payloads import (
    build_restitusi_submit_payload,
    build_restitusi_confirmation_payload,
    build_restitusi_dispute_payload
)
from validators.db_validator import validate_draft_akseptasi, validate_restitusi, validate_sertifikat_dtl, validate_final_status_restitusi
from validators.ui_validator import validate_polis_ui_and_qr
from helpers.ui_acs import check_polis_in_acs, check_sor_in_acs
from helpers.ui_fms import create_jurnal_bbk_restitusi
from utils.email_utils import check_restitusi_email
from config.config import GMAIL_USERNAME, GMAIL_APP_PASSWORD

from api.endpoints import RESTITUSI_SUBMIT, RESTITUSI_CONFIRMATION, RESTITUSI_DISPUTES, RESTITUSI_DETAIL, RESTITUSI_NOTA
from utils.logger import get_logger

logger = get_logger(__name__)

def run_restitusi_flow(api_client, db_client, tc_id, nomor_transaksi, nomor_loan, policy_no, premi, tenor, evidence_collector, plus_days, expect_sanggahan=False, mock_paid_off=True, fake_loan=False, transaction_type="REFUND", overcharge=False, skip_ui=False, double_submit=False, is_hold=False, illegal_dispute=False, undercharge_confirm=False, illegal_confirm=False):
    """
    Executes the Restitusi Flow handling both happy paths and negative cases.
    """
    
    # Step 1: Mock payment status in ACS Staging DB (unless testing unpaid policy)
    if mock_paid_off:
        logger.info(f"[{tc_id}] Mocking premium payment in ACS DB for Policy: {policy_no}")
        execute_acs_update(QUERY_ACS_UPDATE_PREMIUM_PAIDOFF, (policy_no,))
        time.sleep(2)
    
    # Step 2: Submit Restitusi
    submit_loan = nomor_loan + "XXX" if fake_loan else nomor_loan
    submit_payload = build_restitusi_submit_payload(submit_loan, plus_days, premi, tenor, transaction_type, overcharge)
    
    logger.info(f"[{tc_id}] Submitting Restitusi: {submit_payload}")
    res_submit = api_client.post(RESTITUSI_SUBMIT, submit_payload)
    evidence_collector.add_api_evidence(tc_id, "Submit Restitusi", RESTITUSI_SUBMIT, submit_payload, res_submit.json(), res_submit.status_code)
    
    # Handle Negative Cases early exit
    if (not mock_paid_off and not is_hold) or fake_loan or transaction_type != "REFUND" or overcharge:
        assert res_submit.status_code != 200, f"Expected error for negative case, but got 200 OK: {res_submit.text}"
        logger.info(f"[{tc_id}] Negative test passed with status {res_submit.status_code}: {res_submit.text}")
        return True
        
    assert res_submit.status_code == 200, f"Submit Restitusi failed: {res_submit.text}"
    
    if double_submit:
        logger.info(f"[{tc_id}] Menunggu 5 detik sebelum submit ulang (Double Submit)...")
        time.sleep(5)
        logger.info(f"[{tc_id}] Submitting Restitusi AGAIN for double_submit negative test")
        res_submit_2 = api_client.post(RESTITUSI_SUBMIT, submit_payload)
        evidence_collector.add_api_evidence(tc_id, "Submit Restitusi Ke-2", RESTITUSI_SUBMIT, submit_payload, res_submit_2.json(), res_submit_2.status_code)
        
        assert res_submit_2.status_code != 200, f"Expected error for double submit, but got 200 OK: {res_submit_2.text}"
        logger.info(f"[{tc_id}] Double submit test passed with status {res_submit_2.status_code}: {res_submit_2.text}")
        return True
    
    # --- HANDLING HOLD FLOW ---
    if is_hold:
        logger.info(f"[{tc_id}] Memeriksa status Hold (12) karena premi belum lunas...")
        # Check DB for status 12
        time.sleep(3)
        db_res = db_client.execute_query(QUERY_GET_RESTITUSI, (nomor_transaksi,))
        # Assert message from api
        assert "diproses setelah status premi terkonfirmasi lunas" in res_submit.text, f"Expected hold message not found: {res_submit.text}"
        
        logger.info(f"[{tc_id}] Patching premium ke Lunas...")
        execute_acs_update(QUERY_ACS_UPDATE_PREMIUM_PAIDOFF, (policy_no,))
        
        logger.info(f"[{tc_id}] Menunggu scheduler memproses (Status 12 -> 13)...")
        status_13_reached = False
        for _ in range(30):
            time.sleep(10)
            check_q = "SELECT status_akseptasi FROM t_sp2k_submission WHERE nomor_transaksi = %s"
            curr = db_client.execute_query(check_q, (nomor_transaksi,))
            if curr and str(curr[0].get('status_akseptasi')) == '13':
                status_13_reached = True
                break
        assert status_13_reached, "Status tidak berubah ke 13 setelah 5 menit"
        logger.info(f"[{tc_id}] Status berhasil berubah ke 13, melanjutkan flow normal...")

    # --- GET KALKULASI ASKRINDO ---
    time.sleep(3)
    db_res = db_client.execute_query(QUERY_GET_RESTITUSI, (nomor_transaksi,))
    kalkulasi_askrindo = submit_payload["nilai_pengajuan"]
    
    # --- HANDLING UNDERCHARGE CONFIRM (TC-59) ---
    if undercharge_confirm:
        logger.info(f"[{tc_id}] Melakukan konfirmasi dengan nilai lebih rendah dari pengajuan...")
        conf_value = float(kalkulasi_askrindo) - 10000
        conf_payload = build_restitusi_confirmation_payload(nomor_loan, "DISETUJUI", nilai=conf_value)
        res_conf = api_client.post(RESTITUSI_CONFIRMATION, conf_payload)
        assert res_conf.status_code == 200, f"Confirmation undercharge failed: {res_conf.text}"
        evidence_collector.add_api_evidence(tc_id, "Konfirmasi Lebih Rendah", RESTITUSI_CONFIRMATION, conf_payload, res_conf.json(), res_conf.status_code)
        
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="AGREED", tahap_name="Final Validation (Lowest Value)")
        return True
        
    # --- HANDLING ILLEGAL DISPUTE (TC-61) ---

    # --- HANDLING ILLEGAL CONFIRM (TC-64) ---
    if illegal_confirm:
        logger.info(f"[{tc_id}] Memaksa Konfirmasi (DISETUJUI) dengan nilai > pengajuan awal...")
        illegal_value = float(kalkulasi_askrindo) + 50000
        conf_payload = build_restitusi_confirmation_payload(nomor_loan, "DISETUJUI", nilai=illegal_value)
        res_conf = api_client.post(RESTITUSI_CONFIRMATION, conf_payload)
        
        assert res_conf.status_code != 200, f"Expected illegal confirm to fail, but got 200 OK: {res_conf.text}"
        evidence_collector.add_api_evidence(tc_id, "Konfirmasi Ilegal (Negative)", RESTITUSI_CONFIRMATION, conf_payload, res_conf.json() if res_conf.content else res_conf.text, res_conf.status_code)
        return True

    if illegal_dispute:

        logger.info(f"[{tc_id}] Memaksa Sanggahan Ilegal dengan nilai > pengajuan awal...")
        illegal_value = float(kalkulasi_askrindo) + 50000
        conf_payload = build_restitusi_confirmation_payload(nomor_loan, "SANGGAHAN", nilai=illegal_value)
        res_conf = api_client.post(RESTITUSI_CONFIRMATION, conf_payload)
        
        assert res_conf.status_code == 200, f"Expected 200 OK for illegal dispute recording, got: {res_conf.text}"
        evidence_collector.add_api_evidence(tc_id, "Sanggahan Ilegal (Tertahan)", RESTITUSI_CONFIRMATION, conf_payload, res_conf.json() if res_conf.content else res_conf.text, res_conf.status_code)
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="SANGGAHAN", tahap_name="Validasi Sanggahan Tertahan")
        return True
    
    if not expect_sanggahan:
        # Step 3 (Happy Path): Konfirmasi Setuju
        # Askrindo calculation is used
        conf_payload = build_restitusi_confirmation_payload(nomor_loan, "DISETUJUI", nilai=kalkulasi_askrindo)
        
        # Add retry loop to wait for backend to change status
        for i in range(15):
            res_conf = api_client.post(RESTITUSI_CONFIRMATION, conf_payload)
            if res_conf.status_code == 200:
                break
            time.sleep(2)
            
        assert res_conf.status_code == 200, f"Confirmation failed: {res_conf.text}"
        evidence_collector.add_api_evidence(tc_id, "Konfirmasi Setuju", RESTITUSI_CONFIRMATION, conf_payload, res_conf.json(), res_conf.status_code)
        
        # Final Validation (nominal_disetujui should be populated)
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="AGREED", tahap_name="Final Validation (AGREED)")
        
    else:
        # Step 3 (Sanggahan Flow)
        # We propose a value > kalkulasi_askrindo to trigger COUNTER
        sanggahan_value = float(kalkulasi_askrindo) + 50000
        conf_payload = build_restitusi_confirmation_payload(nomor_loan, "SANGGAHAN", nilai=sanggahan_value)
        
        # Add retry loop
        for i in range(15):
            res_conf = api_client.post(RESTITUSI_CONFIRMATION, conf_payload)
            if res_conf.status_code == 200:
                break
            time.sleep(2)
            
        assert res_conf.status_code == 200, f"Sanggahan failed: {res_conf.text}"
        assert res_conf.status_code == 200, f"Sanggahan failed: {res_conf.text}"
        evidence_collector.add_api_evidence(tc_id, "Konfirmasi Sanggah", RESTITUSI_CONFIRMATION, conf_payload, res_conf.json(), res_conf.status_code)
        
        # Validation (nominal_disetujui should be NULL)
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="COUNTER", tahap_name="Validation (COUNTER)")
        
        # Step 4: Dispute
        # Propose a value <= kalkulasi_askrindo to get accepted
        dispute_value = float(kalkulasi_askrindo)
        dispute_payload = build_restitusi_dispute_payload(nomor_loan, dispute_value, sanggahan_value)
        res_disp = api_client.post(RESTITUSI_DISPUTES, dispute_payload)
        assert res_disp.status_code == 200, f"Dispute failed: {res_disp.text}"
        evidence_collector.add_api_evidence(tc_id, "Dispute Lanjutan", RESTITUSI_DISPUTES, dispute_payload, res_disp.json(), res_disp.status_code)
        
        # Final Validation (nominal_disetujui should be populated now)
        time.sleep(2)
        validate_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector, expected_status="AGREED", tahap_name="Final Validation (AGREED after Dispute)")
        
    # Validasi Akhir Status Akseptasi
    validate_draft_akseptasi(db_client, nomor_transaksi, tc_id, evidence_collector, tahap_name="Final Restitusi State")
    
    # Validasi Jurnal & Sertifikat DTL Endorsement
    logger.info("Menunggu data endorsement (/C) masuk ke database t_sertifikat_dtl...")
    for i in range(15):
        db_res = db_client.execute_query(QUERY_GET_SERTIFIKAT_DTL_ENDORSEMENT, (policy_no,))
        if db_res and len(db_res) > 0:
            logger.info("Data endorsement (/C) telah berhasil digenerate di Database!")
            break
        logger.info(f"Percobaan ke-{i+1}/15: Data endorsement belum ada di DB. Menunggu 5 detik...")
        time.sleep(5)
        
    validate_sertifikat_dtl(db_client, policy_no, tc_id, evidence_collector, tahap_name="Endorsement Batal/Refund")

    # Detail API hit
    res_detail = api_client.get(f"{RESTITUSI_DETAIL}?nomor_loan={nomor_loan}")
    evidence_collector.add_api_evidence(tc_id, "Get Detail Restitusi", RESTITUSI_DETAIL, {"nomor_loan": nomor_loan}, res_detail.json(), res_detail.status_code)
    
    if not skip_ui:
        # Step 5: Check Endorsement in UI ACS
        endorsement_polis = f"{policy_no}/C"
        logger.info(f"[{tc_id}] Checking Endorsement Polis in ACS UI: {endorsement_polis}")
        try:
            from db.acs_client import wait_for_policy_in_acs
            logger.info("Menunggu sinkronisasi polis endorsement ke ACS UAT...")
            wait_for_policy_in_acs(endorsement_polis, max_retries=15, delay_sec=10)
            
            ui_res = check_polis_in_acs(endorsement_polis)
            for path in ui_res.get("paths", []):
                sys_name = "FMS" if "fms_jurnal" in path else "ACS"
                evidence_collector.add_ui_evidence(tc_id, sys_name, path)
        except Exception as e:
            logger.error(f"Failed to check endorsement in ACS UI: {e}")
            

        # Step 6: Create Jurnal BBK in FMS
        logger.info(f"[{tc_id}] Creating Jurnal BBK in FMS for policy: {endorsement_polis}")
        try:
            no_jurnal = create_jurnal_bbk_restitusi(endorsement_polis, tc_id, evidence_collector)
            if no_jurnal and no_jurnal != "-":
                # Add to test data safely
                if evidence_collector and tc_id in evidence_collector.evidences:
                    current_data = evidence_collector.evidences[tc_id].get("custom_test_data", "")
                    evidence_collector.evidences[tc_id]["custom_test_data"] = current_data + f"\nNo Jurnal BBK: {no_jurnal}"
        except Exception as e:
            logger.error(f"Failed to create Jurnal BBK in FMS: {e}")
            pass
        
    # Download Receipt PDF
    if True:
        try:
            logger.info(f"[{tc_id}] Memanggil API Receipt PDF...")
            pdf_url = RESTITUSI_NOTA
            res_pdf = api_client.get(pdf_url, params={"no_loan": nomor_loan})
            
            # Since it's a PDF, we can't json serialize it in the evidence, so we pass dummy json or raw text
            pdf_data = {"filename": f"receipt_{nomor_loan}.pdf", "size_bytes": len(res_pdf.content)} if res_pdf.status_code == 200 else res_pdf.text
            evidence_collector.add_api_evidence(tc_id, "Download Receipt PDF", "GET", {"no_loan": nomor_loan}, pdf_data, res_pdf.status_code)
            
            # Use PyMuPDF (fitz) to convert PDF to image
            try:
                import fitz
                import os
                
                pdf_evidence_dir = "evidence/restitusi"
                os.makedirs(pdf_evidence_dir, exist_ok=True)
                ss_pdf_path = f"{pdf_evidence_dir}/receipt_{tc_id}.png"
                
                # Convert the first page of the PDF to image
                doc = fitz.open(stream=res_pdf.content, filetype="pdf")
                if len(doc) > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap(dpi=150)
                    pix.save(ss_pdf_path)
                    evidence_collector.add_ui_evidence(tc_id, "Restitusi Nota (Bukti Bayar)", ss_pdf_path)
                else:
                    logger.warning(f"PDF Bukti Bayar kosong (0 halaman)")
                    
            except Exception as e:
                logger.warning(f"Gagal convert PDF Bukti Bayar ke PNG: {e}")
            
            assert res_pdf.status_code == 200, f"Gagal mendownload PDF Receipt: {res_pdf.status_code}"
        except Exception as e:
            logger.error(f"Gagal memanggil API Receipt PDF: {e}")


    if not skip_ui:
        # Menunggu scheduler memproses jurnal (status 16)
        logger.info(f"[{tc_id}] Menunggu scheduler memproses jurnal (status 16)...")
        max_retries = 60 # 60 * 2 = 600 seconds (2 menit)
        for i in range(max_retries):
            try:
                query = "SELECT status_akseptasi FROM t_sp2k_submission WHERE nomor_transaksi = %s"
                temp_res = db_client.execute_query(query, (nomor_transaksi,))
                if temp_res and len(temp_res) > 0:
                    if str(temp_res[0].get('status_akseptasi')) == '16':
                        logger.info(f"[{tc_id}] Scheduler selesai memproses pada percobaan ke-{i+1}.")
                        # Save to report
                        evidence_collector.add_db_evidence(
                            tc_id, 
                            f"[{nomor_transaksi}] {query}", 
                            temp_res
                        )
                        break
            except Exception:
                pass
            time.sleep(2)
            
        # Mengecek Submenu SOR di ACS UI
        endorsement_polis = f"{policy_no}/C"
        logger.info(f"[{tc_id}] Mengecek SOR Polis Endorsement di ACS: {endorsement_polis}")
        try:
            sor_res = check_sor_in_acs(endorsement_polis)
            for path in sor_res.get("paths", []):
                evidence_collector.add_ui_evidence(tc_id, "ACS SOR", path)
        except Exception as e:
            logger.error(f"Failed to check SOR in ACS UI: {e}")

    logger.info(f"[{tc_id}] Memvalidasi Final Status Restitusi dan No Jurnal di Database...")
    validate_final_status_restitusi(db_client, nomor_transaksi, tc_id, evidence_collector)

    # Step 7: Verifikasi Email Notifikasi Restitusi
    if GMAIL_USERNAME and GMAIL_APP_PASSWORD:
        logger.info(f"[{tc_id}] Memulai pengecekan email notifikasi...")
        check_restitusi_email(GMAIL_USERNAME, GMAIL_APP_PASSWORD, nomor_loan, tc_id, evidence_collector)
    else:
        logger.warning(f"[{tc_id}] GMAIL_USERNAME atau GMAIL_APP_PASSWORD tidak diset di .env. Skip cek email.")
        
    return True
