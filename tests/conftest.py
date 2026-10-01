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

def pytest_addoption(parser):
    parser.addoption("--tester", action="store", default=None, help="Name of the tester for reports (useful for CI/CD)")

def pytest_configure(config):
    tester = config.getoption("--tester")
    if tester:
        os.environ["PYTEST_TESTER_NAME"] = tester

def pytest_collection_modifyitems(config, items):
    for item in items:
        # Dynamically add marker for tc_id (e.g., 'TC-1' -> @pytest.mark.TC_1)
        if hasattr(item, 'callspec') and 'tc_id' in item.callspec.params:
            tc_id = item.callspec.params['tc_id']
            marker_name = tc_id.replace('-', '_')
            item.add_marker(getattr(pytest.mark, marker_name))

def pytest_sessionstart(session):
    prefix = ""

    # Comprehensive cleanup of all evidence and report files from previous runs
    old_files = []
    
    # Reports
    old_files.extend(glob.glob(f"reports/{prefix}epolis_*.png"))
    for ext in ["*.pdf", "*.docx", "*.xlsx", "*.html"]:
        old_files.extend(glob.glob(f"reports/{prefix}Automation_Report_Batch_{ext}"))
        old_files.extend(glob.glob(f"reports/{prefix}Automation_Report_Batch_*_{ext}"))
        old_files.extend(glob.glob(f"reports/{prefix}Defect_Report_{ext}"))
        old_files.extend(glob.glob(f"reports/{prefix}Defect_Report_*_{ext}"))
        
    # Evidence directories (ACS, FMS, Emails)
    for ext in ["*.png", "*.html", "*.txt"]:
        old_files.extend(glob.glob(f"evidence/*/{prefix}*{ext}"))
        old_files.extend(glob.glob(f"evidence/*/*/{prefix}*{ext}"))
        
    for old in old_files:
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
        
        # Removed timestamp so reports always overwrite the old ones
        
        pdf_filename = f"reports/{prefix}Automation_Report_Batch.pdf"
        report_generator.generate_pdf(evidences, pdf_filename)
        
        docx_filename = f"reports/{prefix}Automation_Report_Batch.docx"
        report_generator.generate_docx(evidences, docx_filename)
        
        excel_filename = f"reports/{prefix}Automation_Report_Batch.xlsx"
        report_generator.generate_excel(evidences, excel_filename)
        
        report_generator.generate_defect_reports(evidences, prefix)
        
        logger.info(f"Reports generated successfully: {pdf_filename}, {docx_filename}, {excel_filename}, and defect reports if any")
