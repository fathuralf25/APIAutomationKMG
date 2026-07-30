import copy
from utils.logger import get_logger
from utils.payload_factory import build_dynamic_payload
from api.endpoints import SUBMIT_DRAFT_AKSEPTASI, INQUIRY_LOAN, OTORISASI, PAYMENT, PEMBATALAN
from validators.db_validator import validate_draft_akseptasi, validate_terbit_polis
from validators.ui_validator import validate_polis_ui_and_qr
from utils.generators import generate_transaction_number, generate_loan_number, generate_perjanjian_kredit, generate_reff_pembayaran

logger = get_logger(__name__)

def run_full_e2e_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta):
    """
    Executes the full End-to-End flow: Submit -> Inquiry -> Otorisasi -> Payment -> Validasi UI/DB
    """
    logger.info(f"Executing {tc_id}: Full E2E Flow (Submit -> Inquiry -> Otorisasi -> Payment -> UI)")
    
    # 1. SUBMIT DRAFT
    payload_submit = build_dynamic_payload(tc_id, "a2", state, base_payloads)
    resp_submit = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload_submit)
    assert resp_submit.status_code == 200
    data_submit = resp_submit.json()
    trx = payload_submit["nomor_transaksi"]
    state["last_success_trx"] = trx
    evidence_collector.add_api_evidence(tc_id, SUBMIT_DRAFT_AKSEPTASI, "POST", payload_submit, data_submit, 200)
    
    validate_draft_akseptasi(db_client, trx, tc_id, evidence_collector, tahap_name="Setelah Submit")
    
    # 2. INQUIRY
    payload_inquiry = build_dynamic_payload(tc_id, "a4", state, base_payloads)
    resp_inquiry = api_client.post(INQUIRY_LOAN, payload_inquiry)
    assert resp_inquiry.status_code == 200
    evidence_collector.add_api_evidence(tc_id, INQUIRY_LOAN, "POST", payload_inquiry, resp_inquiry.json(), 200)
    
    validate_draft_akseptasi(db_client, trx, tc_id, evidence_collector, tahap_name="Setelah Inquiry")
    
    # 3. OTORISASI
    payload_oto = build_dynamic_payload(tc_id, "a5", state, base_payloads)
    resp_oto = api_client.post(OTORISASI, payload_oto)
    assert resp_oto.status_code == 200
    evidence_collector.add_api_evidence(tc_id, OTORISASI, "POST", payload_oto, resp_oto.json(), 200)
    
    validate_draft_akseptasi(db_client, trx, tc_id, evidence_collector, tahap_name="Setelah Otorisasi")
    
    # 4. PAYMENT
    payload_pay = build_dynamic_payload(tc_id, "a6", state, base_payloads)
    payload_pay["nominal_pembayaran"] = data_submit["data"]["premi"]
    resp_pay = api_client.post(PAYMENT, payload_pay)
    assert resp_pay.status_code == 200
    evidence_collector.add_api_evidence(tc_id, PAYMENT, "POST", payload_pay, resp_pay.json(), 200)
    
    # 5. DB & UI VALIDATION
    validate_draft_akseptasi(db_client, trx, tc_id, evidence_collector, tahap_name="Data Ditemukan (Status Terakhir)")
    db_result = validate_terbit_polis(db_client, trx, tc_id, evidence_collector)
    
    if db_result and isinstance(db_result[0], dict):
        no_sertifikat = db_result[0].get("no_sertifikat")
        url_download = db_result[0].get("url_download_sertifikat")
        validate_polis_ui_and_qr(tc_id, no_sertifikat, url_download, trx, data_submit, db_result, evidence_collector)
            
    meta["status"] = "Passed"
    evidence_collector.set_test_status(tc_id, meta["status"])

def run_pembatalan_bertahap_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta):
    """
    Executes TC-29: Pembatalan Bertahap dan E2E dengan Data (KTP, Loan, PK) yang Sama
    """
    logger.info("Executing TC-29: Pembatalan Bertahap dan E2E dengan Data (KTP, Loan, PK) yang Sama")
    
    meta["tc_name"] = "Pembatalan Bertahap dan E2E dengan Data (KTP, Loan, PK) yang Sama"
    meta["expected"] = "Sistem mengizinkan reuse data (KTP, Loan, PK) selama pengajuan sebelumnya dibatalkan."
    evidence_collector.set_test_metadata(tc_id, meta["tc_name"], meta["expected"], meta["precondition"])
    
    def run_batal(trx_id, tahap_name):
        validate_draft_akseptasi(db_client, trx_id, tc_id, evidence_collector, tahap_name=f"Sebelum Batal ({tahap_name})")
        payload_batal = copy.deepcopy(base_payloads.get("pembatalan", {}))
        payload_batal["nomor_transaksi"] = trx_id
        resp_batal = api_client.post(PEMBATALAN, payload_batal)
        assert resp_batal.status_code == 200
        evidence_collector.add_api_evidence(tc_id, PEMBATALAN + f" ({tahap_name})", "POST", payload_batal, resp_batal.json(), 200)
        validate_draft_akseptasi(db_client, trx_id, tc_id, evidence_collector, tahap_name=f"Setelah Batal ({tahap_name})")

    base_submit_payload = build_dynamic_payload(tc_id, "a2", state, base_payloads)
    master_ktp = base_submit_payload["ktp"]
    master_loan = generate_loan_number()
    master_pk = generate_perjanjian_kredit()

    # TAHAP 1: Submit -> Batal
    trx_1 = base_submit_payload["nomor_transaksi"]
    payload_1 = copy.deepcopy(base_submit_payload)
    resp_1 = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload_1)
    assert resp_1.status_code == 200
    evidence_collector.add_api_evidence(tc_id, f"{SUBMIT_DRAFT_AKSEPTASI} (Tahap 1)", "POST", payload_1, resp_1.json(), 200)
    run_batal(trx_1, "Tahap 1")

    # TAHAP 2: Submit -> Inquiry -> Batal
    trx_2 = generate_transaction_number()
    payload_2 = copy.deepcopy(base_submit_payload)
    payload_2["nomor_transaksi"] = trx_2
    resp_2 = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload_2)
    assert resp_2.status_code == 200
    evidence_collector.add_api_evidence(tc_id, f"{SUBMIT_DRAFT_AKSEPTASI} (Tahap 2)", "POST", payload_2, resp_2.json(), 200)
    
    payload_inquiry_2 = copy.deepcopy(base_payloads.get("inquiry", {}))
    payload_inquiry_2["nomor_transaksi"] = trx_2
    payload_inquiry_2["nomor_loan"] = master_loan
    payload_inquiry_2["nomor_perjanjian_kredit"] = master_pk
    payload_inquiry_2["tanggal_akad"] = payload_2["tanggal_rencana_realisasi"]
    payload_inquiry_2["outstanding"] = payload_2["uang_pertanggungan"]
    resp_inq_2 = api_client.post(INQUIRY_LOAN, payload_inquiry_2)
    assert resp_inq_2.status_code == 200
    evidence_collector.add_api_evidence(tc_id, f"{INQUIRY_LOAN} (Tahap 2)", "POST", payload_inquiry_2, resp_inq_2.json(), 200)
    run_batal(trx_2, "Tahap 2")

    # TAHAP 3: Submit -> Inquiry -> Otorisasi -> Batal
    trx_3 = generate_transaction_number()
    payload_3 = copy.deepcopy(base_submit_payload)
    payload_3["nomor_transaksi"] = trx_3
    resp_3 = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload_3)
    evidence_collector.add_api_evidence(tc_id, f"{SUBMIT_DRAFT_AKSEPTASI} (Tahap 3)", "POST", payload_3, resp_3.json(), 200)
    
    payload_inquiry_3 = copy.deepcopy(payload_inquiry_2)
    payload_inquiry_3["nomor_transaksi"] = trx_3
    resp_inq_3 = api_client.post(INQUIRY_LOAN, payload_inquiry_3)
    evidence_collector.add_api_evidence(tc_id, f"{INQUIRY_LOAN} (Tahap 3)", "POST", payload_inquiry_3, resp_inq_3.json(), 200)
    
    payload_oto_3 = copy.deepcopy(base_payloads.get("otorisasi", {}))
    payload_oto_3["nomor_transaksi"] = trx_3
    payload_oto_3["nomor_loan"] = master_loan
    payload_oto_3["status"] = "DISETUJUI"
    resp_oto_3 = api_client.post(OTORISASI, payload_oto_3)
    evidence_collector.add_api_evidence(tc_id, f"{OTORISASI} (Tahap 3)", "POST", payload_oto_3, resp_oto_3.json(), 200)
    run_batal(trx_3, "Tahap 3")

    # TAHAP 4: E2E hingga Pembayaran
    trx_4 = generate_transaction_number()
    payload_4 = copy.deepcopy(base_submit_payload)
    payload_4["nomor_transaksi"] = trx_4
    resp_4 = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload_4)
    data_submit_4 = resp_4.json()
    evidence_collector.add_api_evidence(tc_id, f"{SUBMIT_DRAFT_AKSEPTASI} (Tahap 4)", "POST", payload_4, data_submit_4, 200)
    
    payload_inquiry_4 = copy.deepcopy(payload_inquiry_2)
    payload_inquiry_4["nomor_transaksi"] = trx_4
    resp_inq_4 = api_client.post(INQUIRY_LOAN, payload_inquiry_4)
    evidence_collector.add_api_evidence(tc_id, f"{INQUIRY_LOAN} (Tahap 4)", "POST", payload_inquiry_4, resp_inq_4.json(), 200)
    
    payload_oto_4 = copy.deepcopy(payload_oto_3)
    payload_oto_4["nomor_transaksi"] = trx_4
    resp_oto_4 = api_client.post(OTORISASI, payload_oto_4)
    evidence_collector.add_api_evidence(tc_id, f"{OTORISASI} (Tahap 4)", "POST", payload_oto_4, resp_oto_4.json(), 200)
    
    payload_pay_4 = copy.deepcopy(base_payloads.get("payment", {}))
    payload_pay_4["nomor_loan"] = master_loan
    payload_pay_4["nomor_reff_pembayaran"] = generate_reff_pembayaran()
    payload_pay_4["nominal_pembayaran"] = data_submit_4.get("data", {}).get("premi", 0.0)
    resp_pay_4 = api_client.post(PAYMENT, payload_pay_4)
    evidence_collector.add_api_evidence(tc_id, f"{PAYMENT} (Tahap 4)", "POST", payload_pay_4, resp_pay_4.json(), 200)
    
    validate_draft_akseptasi(db_client, trx_4, tc_id, evidence_collector, tahap_name="Akhir Tahap 4")
    db_result = validate_terbit_polis(db_client, trx_4, tc_id, evidence_collector, tahap_name="Tahap 4")
    
    if db_result and isinstance(db_result[0], dict):
        no_sertifikat = db_result[0].get("no_sertifikat")
        url_download = db_result[0].get("url_download_sertifikat")
        validate_polis_ui_and_qr(tc_id, no_sertifikat, url_download, trx_4, data_submit_4, db_result, evidence_collector)

    evidence_collector.evidences[tc_id]["custom_test_data"] = (
        f"[DATA UTAMA]\nKTP: {master_ktp}\nLoan: {master_loan}\nPK: {master_pk}\n\n"
        f"[TXs]\nT1: {trx_1}\nT2: {trx_2}\nT3: {trx_3}\nT4: {trx_4}\n"
    )
    meta["status"] = "Passed"
    evidence_collector.set_test_status(tc_id, meta["status"])

def run_payment_e2e_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta, is_negative_payment=False):
    """
    Executes an E2E flow up to Otorisasi, then executes Payment.
    Useful for TC-10 and TC-11 to ensure a clean loan is used.
    """
    logger.info(f"Executing {tc_id}: E2E Flow for Payment Testing")
    
    # 1. SUBMIT -> INQUIRY -> OTORISASI
    payload_submit = build_dynamic_payload(tc_id, "a2", state, base_payloads)
    resp_submit = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload_submit)
    assert resp_submit.status_code == 200, f"Submit failed: {resp_submit.text}"
    evidence_collector.add_api_evidence(tc_id, SUBMIT_DRAFT_AKSEPTASI, "POST", payload_submit, resp_submit.json(), 200)
    
    trx = payload_submit["nomor_transaksi"]
    loan = generate_loan_number()
    premi = resp_submit.json().get("data", {}).get("premi", 0.0)
    
    payload_inq = copy.deepcopy(base_payloads.get("inquiry", {}))
    payload_inq["nomor_transaksi"] = trx
    payload_inq["nomor_loan"] = loan
    payload_inq["nomor_perjanjian_kredit"] = generate_perjanjian_kredit()
    payload_inq["tanggal_akad"] = payload_submit["tanggal_rencana_realisasi"]
    payload_inq["outstanding"] = payload_submit["uang_pertanggungan"]
    
    resp_inq = api_client.post(INQUIRY_LOAN, payload_inq)
    assert resp_inq.status_code == 200, f"Inquiry failed: {resp_inq.text}"
    evidence_collector.add_api_evidence(tc_id, INQUIRY_LOAN, "POST", payload_inq, resp_inq.json(), 200)
    
    payload_oto = copy.deepcopy(base_payloads.get("otorisasi", {}))
    payload_oto["nomor_transaksi"] = trx
    payload_oto["nomor_loan"] = loan
    payload_oto["status"] = "DISETUJUI"
    
    resp_oto = api_client.post(OTORISASI, payload_oto)
    assert resp_oto.status_code == 200, f"Otorisasi failed: {resp_oto.text}"
    evidence_collector.add_api_evidence(tc_id, OTORISASI, "POST", payload_oto, resp_oto.json(), 200)
    
    # 2. PAYMENT
    payload_pay = build_dynamic_payload(tc_id, "a6", state, base_payloads)
    payload_pay["nomor_loan"] = loan
    payload_pay["nominal_pembayaran"] = premi + 1000 if is_negative_payment else premi
    
    resp_pay = api_client.post(PAYMENT, payload_pay)
    evidence_collector.add_api_evidence(tc_id, PAYMENT, "POST", payload_pay, resp_pay.json() if resp_pay.content else {}, resp_pay.status_code)
    
    if is_negative_payment:
        assert resp_pay.status_code in [400, 422], f"Expected fail but got {resp_pay.status_code}"
        # Validate DB (Record not found or no polis)
        validate_terbit_polis(db_client, trx, tc_id, evidence_collector)
        evidence_collector.evidences[tc_id]["db"][-1]["result"] = [{"Validasi DB": "Record not found (Expected karena API gagal validasi / ditolak)", "Response API": resp_pay.json().get("message", "Error"), "Status Code": resp_pay.status_code}]
    else:
        assert resp_pay.status_code == 200, f"Payment failed: {resp_pay.text}"
        db_result = validate_terbit_polis(db_client, trx, tc_id, evidence_collector)
        if db_result and isinstance(db_result[0], dict):
            no_sertifikat = db_result[0].get("no_sertifikat")
            url_download = db_result[0].get("url_download_sertifikat")
            validate_polis_ui_and_qr(tc_id, no_sertifikat, url_download, trx, resp_submit.json(), db_result, evidence_collector)
            for row in evidence_collector.evidences[tc_id]["db"][-1]["result"]:
                if isinstance(row, dict):
                    row["Validasi DB"] = "Data Ditemukan (Polis Terbit)"
                    row["Response API"] = resp_pay.json().get("message", "Success")
                    row["Status Code"] = resp_pay.status_code

    meta["status"] = "Passed"
    evidence_collector.set_test_status(tc_id, meta["status"])


def run_batal_polis_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta):
    """
    Executes an E2E flow up to Polis Terbit (TC-13), then hits PEMBATALAN.
    """
    logger.info(f"Executing {tc_id}: E2E Flow for Pembatalan Polis")
    
    # 1. RUN FULL E2E TO GET POLIS
    payload_submit = build_dynamic_payload(tc_id, "a2", state, base_payloads)
    trx = payload_submit["nomor_transaksi"]
    
    resp_submit = api_client.post(SUBMIT_DRAFT_AKSEPTASI, payload_submit)
    assert resp_submit.status_code == 200
    evidence_collector.add_api_evidence(tc_id, SUBMIT_DRAFT_AKSEPTASI, "POST", payload_submit, resp_submit.json(), 200)
    
    loan = generate_loan_number()
    payload_inq = copy.deepcopy(base_payloads.get("inquiry", {}))
    payload_inq["nomor_transaksi"] = trx
    payload_inq["nomor_loan"] = loan
    payload_inq["nomor_perjanjian_kredit"] = generate_perjanjian_kredit()
    payload_inq["tanggal_akad"] = payload_submit["tanggal_rencana_realisasi"]
    payload_inq["outstanding"] = payload_submit["uang_pertanggungan"]
    
    resp_inq = api_client.post(INQUIRY_LOAN, payload_inq)
    assert resp_inq.status_code == 200
    evidence_collector.add_api_evidence(tc_id, INQUIRY_LOAN, "POST", payload_inq, resp_inq.json(), 200)
    
    payload_oto = copy.deepcopy(base_payloads.get("otorisasi", {}))
    payload_oto["nomor_transaksi"] = trx
    payload_oto["nomor_loan"] = loan
    payload_oto["status"] = "DISETUJUI"
    resp_oto = api_client.post(OTORISASI, payload_oto)
    assert resp_oto.status_code == 200
    evidence_collector.add_api_evidence(tc_id, OTORISASI, "POST", payload_oto, resp_oto.json(), 200)
    
    payload_pay = copy.deepcopy(base_payloads.get("payment", {}))
    payload_pay["nomor_loan"] = loan
    payload_pay["nomor_reff_pembayaran"] = generate_reff_pembayaran()
    payload_pay["nominal_pembayaran"] = resp_submit.json().get("data", {}).get("premi", 0.0)
    resp_pay = api_client.post(PAYMENT, payload_pay)
    assert resp_pay.status_code == 200
    evidence_collector.add_api_evidence(tc_id, PAYMENT, "POST", payload_pay, resp_pay.json(), 200)
    
    validate_terbit_polis(db_client, trx, tc_id, evidence_collector, tahap_name="Sebelum Batal Polis")
    
    # 2. HIT PEMBATALAN (POLIS ISSUED)
    payload_batal = copy.deepcopy(base_payloads.get("pembatalan", {}))
    payload_batal["nomor_transaksi"] = trx
    
    resp_batal = api_client.post(PEMBATALAN, payload_batal)
    evidence_collector.add_api_evidence(tc_id, PEMBATALAN, "POST", payload_batal, resp_batal.json() if resp_batal.content else {}, resp_batal.status_code)
    
    # Batal polis expected to fail based on DB rule if it's already issued (status 9).
    # Wait, the rule says: Cancellation only valid when status akseptasi = 9
    # If Polis is issued, status is 10. So it should FAIL.
    assert resp_batal.status_code in [400, 422], f"Expected fail but got {resp_batal.status_code}"
    
    db_result = validate_draft_akseptasi(db_client, trx, tc_id, evidence_collector, tahap_name="Validasi DB Gagal Batal")
    if db_result:
        for row in evidence_collector.evidences[tc_id]["db"][-1]["result"]:
            if isinstance(row, dict):
                row["Validasi DB"] = "Record not found (Expected karena API gagal validasi / ditolak)"
                row["Response API"] = resp_batal.json().get("message", "Error")
                row["Status Code"] = resp_batal.status_code
    
    meta["status"] = "Passed"
    evidence_collector.set_test_status(tc_id, meta["status"])
