import imaplib
import email
from email.header import decode_header
import os
import time
from playwright.sync_api import sync_playwright
from utils.logger import get_logger

logger = get_logger(__name__)

def check_restitusi_email(gmail_username, gmail_app_password, nomor_loan, tc_id, evidence_collector=None, max_retries=12, wait_time=10):
    """
    Connect to Gmail via IMAP, search for the restitution notification for a specific loan,
    extract its HTML content, save it, and take a screenshot using Playwright.
    """
    logger.info(f"[{tc_id}] Menunggu email notifikasi restitusi untuk loan: {nomor_loan}...")
    subject_to_find = f"Pemberitahuan Pembayaran Restitusi - Loan {nomor_loan}"
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        mail.login(gmail_username, gmail_app_password)
    except Exception as e:
        logger.error(f"[{tc_id}] Gagal login IMAP. Periksa kredensial .env. Error: {e}")
        return False

    mail.select("inbox")
    
    html_content = None
    email_found = False

    for attempt in range(max_retries):
        # Search for email with specific subject
        status, messages = mail.search(None, f'SUBJECT "{subject_to_find}"')
        
        if status == "OK" and messages[0]:
            email_ids = messages[0].split()
            if email_ids:
                logger.info(f"[{tc_id}] Email ditemukan! Memproses email terbaru...")
                email_found = True
                latest_email_id = email_ids[-1] # get the latest one
                
                res, msg_data = mail.fetch(latest_email_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Extract body
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                
                                if content_type == "text/html" and "attachment" not in content_disposition:
                                    try:
                                        html_content = part.get_payload(decode=True).decode()
                                        break
                                    except:
                                        pass
                        else:
                            content_type = msg.get_content_type()
                            if content_type == "text/html":
                                try:
                                    html_content = msg.get_payload(decode=True).decode()
                                except:
                                    pass
                            elif content_type == "text/plain":
                                try:
                                    html_content = msg.get_payload(decode=True).decode()
                                    # Wrap in simple HTML if it's plain text
                                    html_content = f"<html><body><pre>{html_content}</pre></body></html>"
                                except:
                                    pass
                break # Email found, exit retry loop
        
        logger.info(f"[{tc_id}] Email belum ditemukan. Menunggu {wait_time} detik... (Percobaan {attempt + 1}/{max_retries})")
        time.sleep(wait_time)
        # Re-select inbox to refresh
        mail.select("inbox")

    mail.logout()

    if not email_found or not html_content:
        logger.warning(f"[{tc_id}] Email notifikasi tidak ditemukan atau tidak memiliki konten setelah {max_retries * wait_time} detik.")
        return False

    # Save HTML to evidence
    evidence_dir = "evidence/emails"
    os.makedirs(evidence_dir, exist_ok=True)
    html_path = os.path.join(evidence_dir, f"email_restitusi_{tc_id}.html")
    screenshot_path = os.path.join(evidence_dir, f"email_restitusi_{tc_id}.png")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    logger.info(f"[{tc_id}] Menyimpan screenshot email ke {screenshot_path}")
    
    # Use playwright to render HTML and take screenshot
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Construct absolute file URI
            abs_html_path = "file://" + os.path.abspath(html_path)
            page.goto(abs_html_path)
            page.wait_for_load_state("networkidle")
            page.screenshot(path=screenshot_path, full_page=True)
            browser.close()
            
        if evidence_collector:
            evidence_collector.add_email_evidence(tc_id, f"Email Notifikasi: {subject_to_find}", screenshot_path)
        return True
    except Exception as e:
        logger.error(f"[{tc_id}] Gagal mengambil screenshot email: {e}")
        return False
