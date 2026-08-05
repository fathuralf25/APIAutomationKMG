import requests
import fitz  # PyMuPDF
import cv2
import numpy as np
from config.config import BASE_URL, API_TOKEN
from utils.logger import get_logger
import os
import glob

logger = get_logger(__name__)

def download_and_scan_policy_qr(policy_no: str, db_url: str = None, trx_no: str = None) -> tuple[str, list]:
    """
    Downloads the policy PDF for a given policy number and scans it for a QR code.
    Returns the decoded QR string, or an error message.
    """
    import urllib.parse
    if db_url:
        parsed = urllib.parse.urlparse(db_url)
        path_query = f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path
        if not path_query:
            path_query = f"/{db_url.lstrip('/')}"
        url = f"http://10.100.20.111:8073{path_query}"
    else:
        url = f"http://10.100.20.111:8073/download/policy?policy_no={policy_no}"
        
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    logger.info(f"Downloading Policy PDF from: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code != 200:
            return f"Gagal download PDF. HTTP Status: {response.status_code}", []
            
        pdf_data = response.content
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        
        qr_results = []
        detector = cv2.QRCodeDetector()
        
        image_paths = []
        
        os.makedirs("reports", exist_ok=True)
        is_trial = os.environ.get("TRIAL_RUN") == "true"
        prefix = "trial_" if is_trial else ""
        

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Save screenshot of the page
            pix = page.get_pixmap(dpi=300) # High DPI for better QR recognition
            safe_policy = policy_no.replace('/', '_')
            trx_part = f"_{trx_no}" if trx_no else ""
            image_path = f"reports/{prefix}epolis_{safe_policy}{trx_part}_page{page_num}.png"
            pix.save(image_path)
            image_paths.append(image_path)
            
            # Scan the full page image for QR codes instead of looking for embedded images
            # This handles QR codes that are drawn as vectors or complex layers
            cv_img = cv2.imread(image_path)
            if cv_img is not None:
                # Use a specialized QR detector if available, otherwise fallback to cv2
                try:
                    from pyzbar.pyzbar import decode
                    decoded_objects = decode(cv_img)
                    for obj in decoded_objects:
                        qr_data = obj.data.decode('utf-8')
                        if qr_data:
                            qr_results.append(qr_data)
                except ImportError:
                    # Fallback to OpenCV if pyzbar is not installed
                    data, bbox, _ = detector.detectAndDecode(cv_img)
                    if data:
                        qr_results.append(data)
                        
        final_qr = "\n\n".join(qr_results) if qr_results else "QR Code tidak ditemukan di dalam dokumen PDF."
        
        # Check if the QR result is a URL. If so, capture its screenshot
        for qr in qr_results:
            if qr.startswith("http://") or qr.startswith("https://"):
                try:
                    from playwright.sync_api import sync_playwright
                    with sync_playwright() as p:
                        browser = p.chromium.launch(headless=False)
                        context = browser.new_context(ignore_https_errors=True)
                        page = context.new_page()
                        
                        logger.info(f"Visiting QR URL: {qr}")
                        page.goto(qr, timeout=30000)
                        
                        # Wait for the checkmark or validity text to render
                        try:
                            # Try to wait up to 5 minutes for the definitive text indicating data is loaded
                            page.get_by_text("Informasi Polis", exact=False).first.wait_for(timeout=300000)
                        except:
                            # If text not found after 5 minutes, just wait an additional 10 seconds to be safe
                            page.wait_for_timeout(10000)
                        
                        safe_policy = policy_no.replace('/', '_')
                        trx_part = f"_{trx_no}" if trx_no else ""
                        qr_ss_path = f"reports/{prefix}epolis_{safe_policy}{trx_part}_qr_validation.png"
                        page.screenshot(path=qr_ss_path, full_page=True)
                        image_paths.append(qr_ss_path)
                        browser.close()
                        
                        final_qr += "\n\n[Status: Berhasil memvalidasi URL QR Code dan screenshot diambil]"
                        break # Only process the first valid URL
                except Exception as e:
                    logger.error(f"Failed to capture QR URL {qr}: {e}")
                    final_qr += f"\n\n[Status: Gagal memvalidasi URL QR Code: {e}]"
                    
        return final_qr, image_paths
            
    except Exception as e:
        logger.error(f"Error scanning QR from PDF: {e}")
        return f"Error scanning QR: {e}", []
