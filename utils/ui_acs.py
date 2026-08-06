import os
import glob
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import time
import logging

logger = logging.getLogger(__name__)

def check_polis_in_acs(nomor_polis: str) -> str:
    """
    Checks the polis in ACS UI and returns the path to the screenshot evidence.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        url = os.getenv("BASE_URL_ACS")
        username = os.getenv("USERNAME_ACS")
        password = os.getenv("PASSWORD_ACS")
        
        is_trial = os.environ.get("TRIAL_RUN") == "true"
        prefix = "trial_" if is_trial else ""
        
        logger.info(f"Opening ACS URL: {url}")
        page.goto(url)
        
        # Login
        username_input = page.get_by_placeholder("YOUR EMAIL/ID", exact=False)
        if username_input.count() == 0:
            username_input = page.locator("input[type='text'], input[type='email']").first
        username_input.fill(username)
        
        password_input = page.locator("input[type='password']").first
        password_input.fill(password)
        
        page.get_by_role("button", name="SIGN IN", exact=False).click()
        
        # Handle Force Login if it appears
        try:
            page.wait_for_timeout(2000)
            # Find button by combining class and text content
            force_login_btn = page.locator("button.btn.btn-shadow.btn-blue-2", has_text="Force Login")
            if force_login_btn.count() > 0:
                force_login_btn.first.click()
                logger.info("Clicked Force Login")
                page.wait_for_load_state("domcontentloaded")
                page.wait_for_timeout(2000)
        except Exception as e:
            logger.info(f"Force login not needed or failed: {e}")
            
        # Navigate Menu
        try:
            # Wait for "ASKRED" to appear
            askred = page.get_by_text("ASKRED", exact=True).first
            askred.wait_for(timeout=30000)
            askred.click()
            
            akseptasi = page.get_by_text("Akseptasi Askred", exact=True).first
            akseptasi.wait_for(timeout=30000)
            akseptasi.click()
            
            inquiry = page.get_by_text("Inquiry Polis", exact=True).first
            inquiry.wait_for(timeout=30000)
            inquiry.click()
            
            # Search Box
            # In the Inquiry page, the search box might not have a placeholder or type='search'
            # We target the first visible text/search input
            search_box = page.locator("input[type='text'], input[type='search']").first
            search_box.wait_for(timeout=30000)
            search_box.fill(nomor_polis)
            page.keyboard.press("Enter")
            
            # Wait for data to load
            page.wait_for_timeout(3000)
            
            # Click the row
            row_element = page.get_by_text(nomor_polis, exact=False).first
            row_element.wait_for(timeout=120000)
            row_element.click()
            
            # Give some time for the modal/details to fully render
            time.sleep(3)
        except Exception as e:
            debug_path = f"evidence/acs/{prefix}debug_error.png"
            os.makedirs("evidence/acs", exist_ok=True)

            page.screenshot(path=debug_path, full_page=True)
            logger.error(f"UI Navigation failed. Debug screenshot saved at {debug_path}. Error: {e}")
            browser.close()
            raise e
        
        os.makedirs("evidence/acs", exist_ok=True)

        # Screenshot General Info
        screenshot_path_general = f"evidence/acs/{prefix}acs_polis_general_{nomor_polis.replace('/', '_')}.png"
        page.screenshot(path=screenshot_path_general, full_page=True)
        logger.info(f"ACS General Evidence saved to {screenshot_path_general}")
        
        # Navigate to Summary
        try:
            summary_tab = page.locator("li[data-name='askred-summary']").first
            summary_tab.wait_for(timeout=30000)
            summary_tab.click()
            page.wait_for_timeout(3000)
            
            screenshot_path_summary = f"evidence/acs/{prefix}acs_polis_summary_{nomor_polis.replace('/', '_')}.png"
            page.screenshot(path=screenshot_path_summary, full_page=True)
            logger.info(f"ACS Summary Evidence saved to {screenshot_path_summary}")
            paths = [screenshot_path_general, screenshot_path_summary]
            
            # Extract Premium value from Summary tab using heuristic regex
            try:
                summary_text = page.locator("body").inner_text()
                # Look for the Summary table header "Currency Premi" and then the "IDR" row
                match = re.search(r'Currency\s+Premi[\s\S]*?IDR\s+([\d\.,]+)', summary_text)
                if match:
                    # The format in UI is 72,500.00 (US format). Remove commas for thousand separator.
                    clean_str = match.group(1).replace(',', '')
                    extracted_premi_acs = float(clean_str)
                else:
                    extracted_premi_acs = 0.0
            except Exception as e:
                logger.warning(f"Failed to extract premi from ACS: {e}")
                extracted_premi_acs = 0.0
                
        except Exception as e:
            logger.warning(f"Failed to capture Summary tab: {e}")
            paths = [screenshot_path_general]
            extracted_premi_acs = 0.0

        # --- FMS Check ---
        try:
            # 1. Extract No Nota
            page.wait_for_timeout(2000)
            
            # Find the paragraph containing /GJ-
            no_nota_el = page.locator("p", has_text="/GJ-").first
            no_nota = ""
            if no_nota_el.count() > 0:
                no_nota = no_nota_el.inner_text().strip()
                logger.info(f"Extracted No Nota: {no_nota}")
            else:
                # If not found, try to find it dynamically or just log error
                logger.warning("Could not find No Nota with /GJ- in ACS Summary")
            
            if no_nota:
                # 2. Login to FMS
                url_fms = os.getenv("BASE_URL_FMS")
                user_fms = os.getenv("USERNAME_FMS")
                pass_fms = os.getenv("PASSWORD_FMS")
                
                logger.info(f"Navigating to FMS URL: {url_fms}")
                page.goto(url_fms)
                page.wait_for_timeout(2000)
                
                # FMS Login
                username_input = page.get_by_placeholder("YOUR EMAIL/ID", exact=False)
                if username_input.count() == 0:
                    username_input = page.locator("input[type='text'], input[type='email']").first
                username_input.fill(user_fms)
                
                password_input = page.locator("input[type='password']").first
                password_input.fill(pass_fms)
                
                logger.info("Clicking Login button for FMS")
                page.locator("button:has-text('Login')").first.click()
                page.wait_for_timeout(3000)
                
                try:
                    force_login_btn = page.locator("button.btn.btn-shadow.btn-blue-2", has_text="Force Login")
                    if force_login_btn.count() > 0:
                        force_login_btn.first.click()
                        page.wait_for_load_state("domcontentloaded")
                        page.wait_for_timeout(2000)
                except:
                    pass

                # 3. Navigate inside FMS
                logger.info("Step: Klik FMS Icon (dollar)")
                page.locator("i.z-icon-usd").first.click(timeout=300000)
                page.wait_for_timeout(2000)
                
                logger.info("Step: Klik Finance & Accounting")
                finance_acc = page.locator("a:has(span:has-text('Finance & Accounting'))").first
                finance_acc.wait_for(state="visible", timeout=300000)
                finance_acc.click(timeout=30000)
                page.wait_for_timeout(1000)
                
                logger.info("Step: Klik Jurnal Umum")
                page.locator("a:has(span:has-text('Jurnal Umum'))").first.click(timeout=60000)
                page.wait_for_timeout(1000)
                
                logger.info("Step: Klik Inquiry Jurnal Umum")
                page.locator("a:has(span:has-text('Inquiry Jurnal Umum (Posted)'))").first.click(timeout=60000)
                page.wait_for_timeout(3000)
                
                # 3. Fill Jurnal Number
                logger.info("Step: Fill No Nota")
                page.locator("input.input-sm.form-control[type='text']").first.fill(no_nota, timeout=60000)
                
                # 4. Select Kantor Pusat -> Askrindo Surabaya
                logger.info("Step: Select Cabang")
                kp_combo = page.locator("input.z-combobox-input").nth(0)
                kp_combo.wait_for(state="visible", timeout=60000)
                kp_combo.click(timeout=60000)
                page.locator("li.z-comboitem", has_text="03 - Askrindo Surabaya").first.click(timeout=60000)
                page.wait_for_timeout(1000)
                
                # 5. Select Periode Akuntansi
                logger.info("Step: Select Periode Akuntansi")
                # Parse month and year from no_nota, e.g. "00161/GJ-03/07/26"
                indonesian_months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
                
                try:
                    parts = no_nota.split('/')
                    month_idx = int(parts[2]) - 1
                    target_month = indonesian_months[month_idx]
                    target_year = "20" + parts[3]
                except Exception as e:
                    logger.warning(f"Failed to parse no_nota {no_nota} for date: {e}")
                    target_month = "Juli"
                    target_year = "2026"
                
                logger.info(f"Parsed Periode Akuntansi: {target_month} {target_year}")
                
                # Transaksi is nth(1), so Bulan is nth(2) and Tahun is nth(3)
                month_combo = page.locator("input.z-combobox-input").nth(2)
                month_combo.wait_for(state="visible", timeout=60000)
                month_combo.click(timeout=60000)
                page.locator("li.z-comboitem", has_text=target_month).first.click(timeout=60000)
                page.wait_for_timeout(1000)
                    
                year_combo = page.locator("input.z-combobox-input").nth(3)
                year_combo.wait_for(state="visible", timeout=60000)
                year_combo.click(timeout=60000)
                page.locator("li.z-comboitem", has_text=target_year).first.click(timeout=60000)
                page.wait_for_timeout(1000)
                    
                # 6. Click Cari
                logger.info("Step: Click Cari")
                page.locator("button.btn.btn-primary:has-text('Cari')").first.click(timeout=60000)
                page.wait_for_timeout(3000)
                
                # 7. Click Result
                logger.info(f"Step: Click Result Link {no_nota}")
                page.locator(f"div.z-listcell-content:has-text('{no_nota}')").first.click(timeout=60000)
                page.wait_for_timeout(3000)
                
                # 8. Screenshot FMS
                logger.info("Step: Capture Screenshot")
                fms_screenshot = f"evidence/acs/{prefix}fms_jurnal_{nomor_polis.replace('/', '_')}.png"
                page.screenshot(path=fms_screenshot, full_page=True)
                logger.info(f"FMS Evidence saved to {fms_screenshot}")
                paths.append(fms_screenshot)
                
        except Exception as e:
            logger.warning(f"Failed to capture FMS UI: {e}")
            
        browser.close()
        return {"paths": paths, "premi_acs": extracted_premi_acs}
