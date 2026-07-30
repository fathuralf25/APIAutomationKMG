import pytest
import pandas as pd

from utils.payload_factory import build_dynamic_payload
from utils.logger import get_logger
from utils.evidence_collector import evidence_collector
from api.endpoints import KALKULATOR, SUBMIT_DRAFT_AKSEPTASI, INQUIRY_LOAN, OTORISASI, PAYMENT, PEMBATALAN

from flows.e2e_flow import run_full_e2e_flow, run_pembatalan_bertahap_flow
from validators.db_validator import validate_draft_akseptasi, validate_terbit_polis
from validators.ui_validator import validate_polis_ui_and_qr

logger = get_logger(__name__)

def get_test_cases_and_metadata():
    try:
        df = pd.read_excel('collections/test_script.xlsx')
        cases, metadata = [], {}
        df.iloc[:, 2] = df.iloc[:, 2].ffill() 
        for _, row in df.iterrows():
            row_list = list(row.values)
            if len(row_list) > 9:
                tc_id = str(row_list[3])
                if pd.isna(row_list[3]) or tc_id == "nan" or tc_id == "TestCase-ID": continue
                if tc_id.startswith("TC-"):
                    cases.append(tc_id)
                    tc_name = str(row_list[4]) if not pd.isna(row_list[4]) else tc_id
                    test_step = str(row_list[7]) if not pd.isna(row_list[7]) else ""
                    precondition = str(row_list[6]) if not pd.isna(row_list[6]) else "1. Buka Postman\n2. Hit API"
                    expected = str(row_list[9]) if not pd.isna(row_list[9]) else "Sistem merespon dengan benar"
                    api_group = str(row_list[2]) if not pd.isna(row_list[2]) else ""
                    
                    if not api_group:
                        ts_lower, exp_lower = test_step.lower(), expected.lower()
                        if any(x in exp_lower or x in ts_lower for x in ["pembayaran", "payment", "polis"]): api_group = "a6"
                        elif "otorisasi" in exp_lower or "otorisasi" in ts_lower: api_group = "a5"
                        elif "inquiry" in exp_lower or "loan" in exp_lower or "inquiry" in ts_lower or "loan" in ts_lower: api_group = "a4"
                        elif "batal" in exp_lower or "cancel" in exp_lower or "batal" in ts_lower or "cancel" in ts_lower: api_group = "a7"
                        else: api_group = "a2"

                    metadata[tc_id] = {
                        "tc_name": tc_name, "status": "Failed", "api": [], "db": [],
                        "expected": expected, "precondition": precondition, "api_group": api_group
                    }
        
        if "TC-10" in cases and "TC-11" in cases:
            idx_10, idx_11 = cases.index("TC-10"), cases.index("TC-11")
            if idx_10 < idx_11: cases[idx_10], cases[idx_11] = cases[idx_11], cases[idx_10]
        return cases, metadata
    except Exception as e:
        logger.error(f"Error reading test cases: {e}")
        return [], {}

TEST_CASES, TEST_METADATA = get_test_cases_and_metadata()

def determine_endpoint(api_group: str) -> str:
    ag = api_group.lower()
    if "a1" in ag or "kalkulasi" in ag: return KALKULATOR
    if "a4" in ag or "inquiry" in ag: return INQUIRY_LOAN
    if "a5" in ag or "otorisasi" in ag: return OTORISASI
    if "a6" in ag or "pembayaran" in ag: return PAYMENT
    if "a7" in ag or "pembatalan" in ag: return PEMBATALAN
    return SUBMIT_DRAFT_AKSEPTASI

@pytest.mark.parametrize("tc_id", TEST_CASES)
def test_dynamic_scenarios(tc_id, api_client, db_client, state, base_payloads):
    logger.info(f"Executing {tc_id} dynamically...")
    meta = TEST_METADATA.get(tc_id, {"tc_name": tc_id, "expected": "Sistem merespon dengan benar", "precondition": "", "api_group": ""})
    
    negative_tcs = ["TC-2", "TC-3", "TC-7", "TC-9", "TC-11", "TC-13", "TC-14", "TC-15", "TC-16", "TC-17", "TC-18", "TC-19", "TC-21", "TC-22", "TC-23", "TC-24", "TC-25", "TC-26", "TC-27", "TC-33", "TC-34", "TC-35"]
    
    original_exp = meta["expected"]
    if not original_exp.startswith("1."): original_exp = f"1. {original_exp}"
    
    # Remove existing "2. ..." if present to avoid duplication
    lines = original_exp.split('\n')
    cleaned_lines = [line for line in lines if not line.strip().startswith("2.")]
    original_exp = "\n".join(cleaned_lines)
    
    meta["expected"] = f"{original_exp}\n2. data tidak kerecord di DB" if tc_id in negative_tcs else f"{original_exp}\n2. data DB sesuai dengan request postman"
    if tc_id == "TC-11":
        meta["expected"] = "1. {\n  \"status\": False,\n  \"message\": \"Nominal Pembayaran tidak sesuai dengan Nominal Premi yang sebenarnya\"\n}\n2. data tidak kerecord di DB"
        
    evidence_collector.set_test_metadata(tc_id, meta["tc_name"], meta["expected"], meta["precondition"])
    
    try:
        from flows.e2e_flow import run_payment_e2e_flow, run_batal_polis_flow
        # 1. Custom E2E Flows
        if tc_id in ["TC-30", "TC-31"]:
            run_full_e2e_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta)
            return
        elif tc_id == "TC-29":
            run_pembatalan_bertahap_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta)
            return
        elif tc_id in ["TC-10", "TC-11"]:
            run_payment_e2e_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta, is_negative_payment=(tc_id == "TC-11"))
            return
        elif tc_id == "TC-13":
            run_batal_polis_flow(tc_id, api_client, db_client, state, base_payloads, evidence_collector, meta)
            return

        # 2. Normal Flow
        endpoint = determine_endpoint(meta["api_group"])
        payload = build_dynamic_payload(tc_id, meta["api_group"], state, base_payloads)
        
        # History injection for E2E display
        if endpoint in [INQUIRY_LOAN, OTORISASI, PAYMENT, PEMBATALAN] and "submit" in state.get("history", {}):
            evidence_collector.evidences[tc_id]["api"].extend(state["history"]["submit"]["api"])
        if endpoint in [OTORISASI, PAYMENT, PEMBATALAN] and "inquiry" in state.get("history", {}):
            evidence_collector.evidences[tc_id]["api"].extend(state["history"]["inquiry"]["api"])
        if endpoint in [PAYMENT] and "otorisasi" in state.get("history", {}):
            evidence_collector.evidences[tc_id]["api"].extend(state["history"]["otorisasi"]["api"])

        response = api_client.post(endpoint, payload)
        evidence_collector.add_api_evidence(tc_id, endpoint, "POST", payload, response.json() if response.content else {}, response.status_code)
        
        # API Status Assertions
        if tc_id in negative_tcs:
            meta["status"] = "Passed" if (endpoint == OTORISASI and response.status_code == 200) or (endpoint != OTORISASI and response.status_code in [400, 422]) else "Failed"
            if tc_id == "TC-11" and (response.json() if response.content else {}).get("message") != "Nominal Pembayaran tidak sesuai dengan Nominal Premi yang sebenarnya":
                meta["status"] = "Failed"
        else:
            meta["status"] = "Passed" if response.status_code == 200 else "Failed"
                
        if meta["status"] == "Passed" and tc_id not in negative_tcs:
            data = response.json() if response.content else {}
            if data.get("data") and isinstance(data["data"], dict) and "premi" in data["data"]:
                state["last_premi"] = data["data"]["premi"]
            if "nomor_transaksi" in payload and endpoint == SUBMIT_DRAFT_AKSEPTASI:
                state["last_success_trx"] = payload["nomor_transaksi"]
                    
        # DB Validation
        if endpoint in [SUBMIT_DRAFT_AKSEPTASI, INQUIRY_LOAN, OTORISASI, PEMBATALAN]:
            identifier = payload.get("nomor_transaksi", state.get("last_success_trx", ""))
            if not identifier and endpoint in [INQUIRY_LOAN, OTORISASI, PEMBATALAN] and "submit" in state.get("history", {}) and state["history"]["submit"]["api"]:
                identifier = state["history"]["submit"]["api"][0]["request_payload"].get("nomor_transaksi", "")
                    
            if identifier:
                db_result = validate_draft_akseptasi(db_client, identifier, tc_id, evidence_collector)
                if not db_result:
                    msg = "Record not found (Expected karena API gagal validasi / ditolak)" if tc_id in negative_tcs else "Record not found"
                    evidence_collector.evidences[tc_id]["db"][-1]["result"] = [{"Validasi DB": msg, "Response API": response.json().get("message", "Success" if response.status_code == 200 else "Error"), "Status Code": response.status_code}]
                else:
                    for row in evidence_collector.evidences[tc_id]["db"][-1]["result"]:
                        if isinstance(row, dict):
                            row["Response API"] = response.json().get("message", "Success" if response.status_code == 200 else "Error")
                            row["Status Code"] = response.status_code
                
        if endpoint == PAYMENT:
            trx = payload.get("nomor_transaksi", state.get("last_success_trx", "TRX-MOCK"))
            if "submit" in state.get("history", {}) and state["history"]["submit"]["api"]:
                trx = state["history"]["submit"]["api"][0]["request_payload"].get("nomor_transaksi", trx)

            db_result = validate_terbit_polis(db_client, trx, tc_id, evidence_collector)
            if db_result and isinstance(db_result[0], dict):
                no_sertifikat = db_result[0].get("no_sertifikat")
                url_download = db_result[0].get("url_download_sertifikat")
                data_sub = {"data": {"premi": state.get("last_premi", 0.0)}}
                validate_polis_ui_and_qr(tc_id, no_sertifikat, url_download, trx, data_sub, db_result, evidence_collector)
                for row in evidence_collector.evidences[tc_id]["db"][-1]["result"]:
                    if isinstance(row, dict):
                        row["Validasi DB"] = "Data Ditemukan (Polis Terbit)"
                        row["Response API"] = response.json().get("message", "Success" if response.status_code == 200 else "Error")
                        row["Status Code"] = response.status_code
            else:
                msg = "Record not found (Expected karena API gagal validasi / ditolak)" if tc_id in negative_tcs else "Record not found (Polis tidak terbit)"
                evidence_collector.evidences[tc_id]["db"][-1]["result"] = [{"Validasi DB": msg, "Response API": response.json().get("message", "Success" if response.status_code == 200 else "Error"), "Status Code": response.status_code}]

        logger.info(f"{tc_id} finished with status {response.status_code}")
        evidence_collector.set_test_status(tc_id, meta["status"])
        
        if meta["status"] == "Passed" and tc_id not in negative_tcs:
            if "history" not in state: state["history"] = {}
            curr_db = evidence_collector.evidences[tc_id]["db"][-1:] if (endpoint in [SUBMIT_DRAFT_AKSEPTASI, PAYMENT] and len(evidence_collector.evidences[tc_id]["db"]) > 0) else []
            step_history = {"api": [{
                "url": endpoint, "method": "POST", "request_payload": payload,
                "response_json": response.json() if response.content else {}, "status_code": response.status_code
            }], "db": curr_db}
            
            if endpoint == SUBMIT_DRAFT_AKSEPTASI:
                state["history"]["submit"] = step_history
                state["history"].pop("inquiry", None)
                state["history"].pop("otorisasi", None)
            elif endpoint == INQUIRY_LOAN:
                state["history"]["inquiry"] = step_history
                state["history"].pop("otorisasi", None)
            elif endpoint == OTORISASI:
                state["history"]["otorisasi"] = step_history
                
        assert meta["status"] == "Passed", f"Test {tc_id} failed. Expected Passed but got Failed. Status code: {response.status_code}, Response: {response.text}"
    
    except Exception as e:
        evidence_collector.set_test_status(tc_id, "Failed")
        raise e
