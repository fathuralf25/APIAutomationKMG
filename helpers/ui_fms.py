import os
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from config.config import BASE_URL_FMS, USERNAME_FMS_SBY as USERNAME_FMS, PASSWORD_FMS_SBY as PASSWORD_FMS
from utils.logger import get_logger

logger = get_logger(__name__)

def create_jurnal_bbk_restitusi(nomor_polis: str, tc_id: str, evidence_collector):
    """
    Automates the creation of BBK journal in FMS for restitution.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        
        try:
            logger.info(f"Opening FMS URL: {BASE_URL_FMS}")
            page.goto(BASE_URL_FMS)
            
            # 1. Login (assuming standard input names/types if not provided)
            page.locator("input[type='text'], input[type='email']").first.fill(USERNAME_FMS)
            page.locator("input[type='password']").first.fill(PASSWORD_FMS)
            page.locator("button", has_text="Login").first.click()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(5)
            
            # 2. Click FMS Dollar Icon
            logger.info("Clicking dollar icon")
            if page.locator("i.z-icon-usd").count() > 0:
                page.locator("i.z-icon-usd").first.click()
            time.sleep(3)
            
            # 3. Handle 'Ganti Password' popup
            try:
                # Check for the Ganti Password window
                popup_title = page.locator("span.z-label", has_text="Ganti Password").first
                popup_title.wait_for(timeout=15000, state="visible")
                logger.info("Handling Ganti Password popup - pressing Escape")
                time.sleep(1)
                
                # Press Escape on the body to ensure it catches the global event
                page.locator("body").press("Escape")
                time.sleep(1)
                
                # 4. Click 'Yes'
                yes_btn = page.locator("button", has_text="Yes").first
                yes_btn.wait_for(timeout=3000, state="visible")
                logger.info("Clicking Yes on confirmation popup")
                yes_btn.click()
                time.sleep(2)
            except Exception as e:
                logger.info(f"No Ganti Password popup found or handled: {e}")
                pass
                
            # 5. Navigate Menu
            logger.info("Navigating Menu FMS")
            page.locator("span.z-menu-text", has_text="Finance & Accounting").click()
            time.sleep(1)
            page.locator("span.z-menu-text", has_text="Bukti Bank").click()
            time.sleep(1)
            page.locator("span.z-menuitem-text", has_text="Entri Bukti Bank").click()
            time.sleep(3)
            
            # 6. Click BBK Button
            page.locator("button.btn-primary", has_text="BBK : Bukti Bank Keluar").click()
            time.sleep(3)
            
            # 7. Fill Form BBK
            logger.info("Filling form BBK")
            
            # Dropdown Periode (Using today's month year e.g., Agustus 2026)
            months = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
            now = datetime.now()
            period_str = f"{months[now.month - 1]} {now.year}"
            
            # Dropdown Periode
            logger.info("Selecting Periode")
            try:
                periode_group = page.locator(".form-group:visible").filter(has_text="Periode")
                if periode_group.count() > 0:
                    periode_group.locator("input.z-combobox-input").first.click(force=True)
                else:
                    page.locator("input.z-combobox-input:visible").nth(0).click(force=True)
                time.sleep(1)
                
                # Check if period exists in dropdown, else assume already selected
                period_item = page.locator("li.z-comboitem:visible", has_text=period_str).first
                if period_item.is_visible():
                    period_item.click()
                    time.sleep(1)
                else:
                    # click again to close dropdown
                    page.locator("body").click()
            except Exception as e:
                logger.warning(f"Could not select Periode, assuming default is correct. Error: {e}")
            
            # Tanggal Akuntansi
            logger.info("Filling Tanggal Akuntansi")
            months_short = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
            today_str = f"{now.day:02d}-{months_short[now.month - 1]}-{now.year}"
            
            tgl_group = page.locator(".form-group:visible").filter(has_text="Tanggal Akuntansi")
            if tgl_group.count() == 0:
                tgl_group = page.locator(".form-group:visible").filter(has_text="Tanggal Akunting")
                
            if tgl_group.count() > 0:
                date_input = tgl_group.locator("input.z-datebox-input").first
                date_input.evaluate("el => el.removeAttribute('readonly')")
                date_input.fill(today_str)
                page.keyboard.press("Tab")
            else:
                date_input = page.locator("input.z-datebox-input:visible").first
                if date_input.count() > 0:
                    date_input.evaluate("el => el.removeAttribute('readonly')")
                    date_input.fill(today_str)
                    page.keyboard.press("Tab")
            time.sleep(1)
            
            # Handle 'Silakan pilih kode bank' popup if it appeared
            try:
                ok_btn = page.locator("button.z-messagebox-button:visible", has_text="OK").first
                if ok_btn.is_visible(timeout=5000):
                    logger.info("Dismissing 'Silakan pilih kode bank' popup")
                    ok_btn.click()
                    time.sleep(1)
            except:
                pass

            # Dropdown Bank Agro (Select2)
            logger.info("Selecting Bank Agro")
            try:
                page.locator("span.select2-selection__placeholder", has_text="Pilih").click(force=True)
                time.sleep(1)
                agro_option = page.locator("li.select2-results__option:visible", has_text="Bank Agro Cabang Surabaya").first
                agro_option.wait_for(state="visible", timeout=5000)
                agro_option.click(force=True)
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Failed to select Bank Agro via placeholder: {e}")
                
            # Pastikan benar-benar terpilih dengan mengecek teksnya
            selected_bank = page.locator("span.select2-selection__rendered").first
            if "Bank Agro" not in selected_bank.inner_text():
                logger.info("Retrying Bank Agro selection")
                page.locator("span.select2-selection--single").first.click(force=True)
                time.sleep(1)
                page.locator("li.select2-results__option:visible", has_text="Bank Agro Cabang Surabaya").first.click(force=True)
                time.sleep(1)
            
            # Dropdown Transaksi
            logger.info("Selecting Transaksi")
            try:
                transaksi_group = page.locator(".form-group:visible").filter(has_text="Transaksi")
                if transaksi_group.count() > 0:
                    transaksi_group.locator("input.z-combobox-input").first.click(force=True)
                else:
                    page.locator("input.z-combobox-input:visible").nth(1).click(force=True)
                time.sleep(1)
                
                trans_item = page.locator("li.z-comboitem:visible", has_text="BBK1 - Pembayaran Bank").first
                if trans_item.is_visible():
                    trans_item.click()
                    time.sleep(1)
                else:
                    page.locator("body").click()
            except Exception as e:
                logger.warning(f"Could not select Transaksi, assuming default. Error: {e}")
            
            # Dibayar Kepada
            logger.info("Filling Dibayar Kepada")
            dibayar_group = page.locator(".form-group:visible").filter(has_text="Dibayar")
            if dibayar_group.count() > 0:
                dibayar_group.locator("input").first.fill("Jatim")
            else:
                # fallback
                page.locator("input.input-sm.form-control[type='text']:not([readonly]):visible").nth(0).fill("Jatim")
            time.sleep(1)
            
            # Dropdown Transfer
            logger.info("Selecting Transfer")
            inputs_combo = page.locator("input.z-combobox-input:visible")
            for i in range(1, inputs_combo.count()):
                inputs_combo.nth(i).click(force=True)
                time.sleep(1)
                transfer_item = page.locator("li.z-comboitem:visible", has_text="Transfer")
                if transfer_item.count() > 0:
                    transfer_item.first.click()
                    time.sleep(1)
                    break
                else:
                    inputs_combo.nth(i).click(force=True)
                    time.sleep(0.5)
            
            # Keterangan
            logger.info("Filling Keterangan")
            page.locator("textarea.form-control:visible").first.fill("Restitusi")
            
            # Nomor Referensi (no polis)
            logger.info("Filling Nomor Referensi")
            ref_group = page.locator(".form-group:visible").filter(has_text="Nomor Ref")
            if ref_group.count() > 0:
                ref_group.locator("input").first.fill(nomor_polis)
            else:
                page.locator("input.input-sm.form-control[type='text']:not([readonly]):visible").nth(1).fill(nomor_polis)
            
            # 8. Multiple Settlement
            page.locator("button.btn-default", has_text="Multiple Settlement").click()
            time.sleep(3)
            
            # 9. Nomor referensi inside modal
            logger.info("Filling Nomor Referensi in Multiple Settlement Modal")
            # Wait for modal to load
            modal = page.locator(".z-window:visible").filter(has_text="Pop up Settlement").first
            modal.wait_for(state="visible", timeout=10000)
            
            # Fill Tanggal Akunting in modal if exists
            try:
                months_short = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
                now = datetime.now()
                today_str = f"{now.day:02d}-{months_short[now.month - 1]}-{now.year}"
                modal_date = modal.locator("input.z-datebox-input:visible").first
                if modal_date.is_visible():
                    modal_date.evaluate("el => el.removeAttribute('readonly')")
                    modal_date.fill(today_str)
            except:
                pass
                
            # Find the form-group containing "Nomor Referensi" and its input
            ref_group = modal.locator(".form-group:visible").filter(has_text="Nomor Referensi")
            ref_group.first.wait_for(state="visible", timeout=5000)
            
            modal_input = ref_group.first.locator("input:visible").first
            modal_input.fill(nomor_polis)
            
            # Kasih jeda setelah isi nomor polis sebelum klik Cari (Sesuai instruksi)
            time.sleep(2)
            
            page.locator("button:visible", has_text="Cari").last.click()
            time.sleep(4)
            
            # 10. Check checkbox for /c
            logger.info("Selecting policy checkbox")
            # Wait for ANY checkbox to appear in the search results
            any_checkbox = modal.locator(".z-listitem-checkbox:visible").first
            try:
                any_checkbox.wait_for(state="visible", timeout=15000)
            except Exception as e:
                logger.warning(f"Timeout waiting for search results checkbox: {e}")
            
            # Try to find the exact endorsement row containing /C or /c
            endorsement_row = page.locator(".z-window-highlighted tr:visible", has_text="/C").filter(has=page.locator(".z-listitem-checkbox"))
            if endorsement_row.count() == 0:
                endorsement_row = page.locator(".z-window-highlighted tr:visible", has_text="/c").filter(has=page.locator(".z-listitem-checkbox"))
                
            if endorsement_row.count() > 0:
                endorsement_row.first.locator(".z-listitem-checkbox:visible").first.click()
            else:
                # Fallback to just clicking the first available checkbox
                any_checkbox.click()
            
            page.locator("button:visible", has_text="Pilih").last.click()
            time.sleep(3)
            
            # 11. Delete Ledger row
            # Filter baris yang visible dan ambil yang terakhir (paling atas di tumpukan modal ZK)
            ledger_row = page.locator("tr:visible", has=page.locator("input[value='Ledger']")).last
            delete_btn = ledger_row.locator("button[title='Hapus']:visible")
            delete_btn.click()
            
            # Wait for the row to be deleted
            time.sleep(4)
            
            # --- DEBUG SCREENSHOT ---
            try:
                debug_ss_path = f"evidence/fms/debug_ledger_{tc_id}.png"
                os.makedirs("evidence/fms", exist_ok=True)
                modal_to_snap = page.locator(".z-window:visible").last
                if modal_to_snap.count() > 0:
                    modal_to_snap.screenshot(path=debug_ss_path)
                else:
                    page.screenshot(path=debug_ss_path, full_page=True)
                logger.info(f"Saved debug screenshot for Ledger deletion to {debug_ss_path}")
            except Exception as e:
                logger.warning(f"Failed to capture debug screenshot: {e}")
            # ------------------------

            page.locator("button.z-messagebox-button", has_text="Yes").click()
            
            # 12. Nominal Kredit
            logger.info("Setting Nominal Kredit")
            
            # Find the label "Debet (Rp) : " and get the value next to it
            try:
                bold_spans = page.locator("span.font-black-bold:visible")
                nominal_str = ""
                for i in range(bold_spans.count()):
                    text = bold_spans.nth(i).inner_text()
                    if "Debet" in text:
                        nominal_str = bold_spans.nth(i + 1).inner_text().strip()
                        break
                        
                if not nominal_str:
                    debit_element = page.locator("span.font-black-bold:visible").first
                    nominal_str = debit_element.inner_text().replace("Debet (Rp) :", "").strip()
                    
                logger.info(f"Extracted Debit Nominal: '{nominal_str}'")
                
                kredit_input = page.locator("input[style*='text-align:right']:not([readonly]):visible").last
                kredit_input.fill(nominal_str)
                time.sleep(1)
                page.keyboard.press("Tab")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Could not set Nominal Kredit: {e}")
                    
            # 13. Workflow Loop: Submit -> Approve -> Posting
            workflow_steps = ["Submit", "Approve", "Posting"]
            for step_name in workflow_steps:
                try:
                    btn = page.locator(f"button:visible", has_text=step_name).last
                    if btn.count() > 0 and btn.is_visible(timeout=5000):
                        logger.info(f"Executing workflow step: {step_name}")
                        
                        try:
                            catatan_group = page.locator(".form-group:visible").filter(has_text="Catatan")
                            if catatan_group.count() > 0:
                                catatan_group.locator("textarea, input").first.fill(f"Auto {step_name}")
                            else:
                                textareas = page.locator("textarea:visible")
                                if textareas.count() > 0:
                                    textareas.last.fill(f"Auto {step_name}")
                        except Exception as e:
                            logger.warning(f"Could not fill Catatan for {step_name}: {e}")
                            
                        btn.click()
                        time.sleep(2)
                        
                        try:
                            yes_btn = page.locator("button.z-messagebox-button:visible", has_text="Yes").last
                            if yes_btn.is_visible(timeout=3000):
                                yes_btn.click()
                                time.sleep(3)
                        except:
                            pass
                        
                        page.wait_for_load_state("domcontentloaded")
                        time.sleep(3)
                        
                        # TRACE: Check for any error popups and RAISE exception so test fails
                        error_popup = page.locator(".z-window-highlighted, .z-messagebox-window, .z-notification").last
                        if error_popup.count() > 0 and error_popup.is_visible(timeout=1000):
                            error_text = error_popup.inner_text()
                            if "berhasil" not in error_text.lower() and "sukses" not in error_text.lower():
                                logger.error(f"FMS Popup Error detected after clicking {step_name}: {error_text}")
                                raise Exception(f"FMS Workflow blocked by error popup: {error_text}")
                except Exception as e:
                    if "FMS Workflow blocked by error popup" in str(e):
                        raise e # Re-raise to fail the test immediately
                    logger.info(f"Workflow step {step_name} skipped or not found: {e}")
                    
            logger.info("FMS Jurnal BBK Restitusi flow completed successfully.")
            
            # Screenshot evidence
            evidence_dir = "evidence/fms"
            os.makedirs(evidence_dir, exist_ok=True)
            screenshot_path = f"{evidence_dir}/bbk_restitusi_{tc_id}.png"
            try:
                page.screenshot(path=screenshot_path)
            except Exception as e:
                logger.warning(f"Screenshot failed: {e}")
            if evidence_collector:
                evidence_collector.add_epolis_evidence(tc_id, f"FMS BBK Jurnal ({nomor_polis})", [screenshot_path])
                
        except Exception as e:
            if "Target page, context or browser has been closed" in str(e):
                logger.error("Page closed by user or system BEFORE completion!")
                raise e
            else:
                logger.error(f"FMS Automation failed: {e}")
                evidence_dir = "evidence/fms"
                os.makedirs(evidence_dir, exist_ok=True)
                try:
                    page.screenshot(path=f"{evidence_dir}/error_{tc_id}.png", full_page=True)
                except:
                    pass
                raise e
        finally:
            if browser:
                browser.close()
