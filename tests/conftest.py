import pytest
import glob
import os
import sys
from datetime import datetime
from typing import Dict, Any, Generator

from config.config import API_TOKEN, CLIENT_ID, CLIENT_SECRET
from helpers.evidence_collector import evidence_collector
from utils.report_generator import report_generator

from api.client import ApiClient
from db.client import DatabaseClient
from utils.logger import get_logger
from utils.payload_loader import load_payload

logger = get_logger(__name__)

@pytest.fixture(scope="session")
def state() -> Dict[str, Any]:
    return {}

@pytest.fixture(scope="session")
def api_client() -> ApiClient:
    token = API_TOKEN
    if CLIENT_ID and CLIENT_SECRET:
        try:
            logger.info("Attempting to auto-generate token using client credentials...")
            jwt_template = load_payload("generate_jwt.json")
            token = ApiClient.generate_token(CLIENT_ID, CLIENT_SECRET, jwt_template)
            logger.info("Token successfully auto-generated.")
        except Exception as e:
            logger.error(f"Failed to auto-generate token: {e}. Falling back to static API_TOKEN.")
            
    client = ApiClient(token=token)
    return client

@pytest.fixture(scope="session")
def db_client() -> Generator[DatabaseClient, None, None]:
    client = DatabaseClient()
    # client.connect()
    yield client
    # client.disconnect()

@pytest.fixture(scope="session")
def base_payloads():
    return {
        "kalkulator": load_payload("kalkulator.json"),
        "submit_draft": load_payload("submit_draft_akseptasi.json"),
        "inquiry": load_payload("inquiry_nomor_loan.json"),
        "otorisasi": load_payload("otorisasi_penyelia_bank.json"),
        "payment": load_payload("notifikasi_pembayaran_premi.json"),
        "pembatalan": load_payload("pembatalan_draft_akseptasi.json")
    }

def pytest_collection_modifyitems(config, items):
    for item in items:
        # Dynamically add marker for tc_id (e.g., 'TC-1' -> @pytest.mark.TC_1)
        if hasattr(item, 'callspec') and 'tc_id' in item.callspec.params:
            tc_id = item.callspec.params['tc_id']
            marker_name = tc_id.replace('-', '_')
            item.add_marker(getattr(pytest.mark, marker_name))

def pytest_sessionstart(session):
    prefix = ""

    # Hapus images dari testing sebelumnya (tidak menghapus yg baru)
    old_images = glob.glob(f"reports/{prefix}epolis_*.png")
    for old in old_images:
        try:
            os.remove(old)
        except Exception:
            pass
            
    # Hapus images ACS dari testing sebelumnya
    old_acs_images = glob.glob(f"evidence/acs/{prefix}acs_polis_*.png")
    for old in old_acs_images:
        try:
            os.remove(old)
        except Exception:
            pass
            
    # Hapus images FMS dari testing sebelumnya
    old_fms_images = glob.glob(f"evidence/acs/{prefix}fms_jurnal_*.png")
    for old in old_fms_images:
        try:
            os.remove(old)
        except Exception:
            pass
            
    old_acs_debug = glob.glob(f"evidence/acs/{prefix}debug_error*.png")
    for old in old_acs_debug:
        try:
            os.remove(old)
        except Exception:
            pass

    # Hapus file report lama dari testing sebelumnya
    old_reports = []
    for ext in ["*.pdf", "*.docx", "*.xlsx"]:
        old_reports.extend(glob.glob(f"reports/{prefix}Automation_Report_Batch_{ext}"))
        old_reports.extend(glob.glob(f"reports/{prefix}Defect_Report_{ext}"))
    
    for old in old_reports:
        try:
            os.remove(old)
        except Exception:
            pass

def pytest_sessionfinish(session, exitstatus):
    """
    Generate the new beautiful Automation Report after tests finish.
    """
    prefix = ""


    evidences = evidence_collector.get_all_evidences()
    if evidences:
        
        logger.info(f"Generating new beautiful PDF/HTML, DOCX, and EXCEL reports from pytest executions (Prefix: {prefix})...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        pdf_filename = f"reports/{prefix}Automation_Report_Batch_{timestamp}.pdf"
        report_generator.generate_pdf(evidences, pdf_filename)
        
        docx_filename = f"reports/{prefix}Automation_Report_Batch_{timestamp}.docx"
        report_generator.generate_docx(evidences, docx_filename)
        
        excel_filename = f"reports/{prefix}Automation_Report_Batch_{timestamp}.xlsx"
        report_generator.generate_excel(evidences, excel_filename)
        
        report_generator.generate_defect_reports(evidences, prefix, timestamp)
        
        logger.info(f"Reports generated successfully: {pdf_filename}, {docx_filename}, {excel_filename}, and defect reports if any")
