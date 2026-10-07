import time
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from config.config import BASE_URL_FMS, USERNAME_FMS_SBY as USERNAME_FMS, PASSWORD_FMS_SBY as PASSWORD_FMS
from utils.logger import get_logger

logger = get_logger(__name__)

def create_jurnal_bbk_restitusi(nomor_polis: str, tc_id: str, evidence_collector):
    no_jurnal = "-"
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
                # Wait for either the popup title or the modal mask
                logger.info("Checking for 'Ganti Password' popup...")
                page.wait_for_selector(".z-modal-mask, span.z-label:has-text('Ganti Password')", timeout=10000, state="visible")
                
                logger.info("Popup detected. Pressing Escape...")
                time.sleep(1)
                
                # Press Escape on the body
                page.locator("body").press("Escape")
                
                # Wait for 'Yes' button and click it
                try:
                    yes_btn = page.locator("button.z-messagebox-button:visible", has_text="Yes").last
                    if yes_btn.count() == 0:
                        yes_btn = page.locator("button:visible", has_text="Yes").last
                    
                    yes_btn.wait_for(timeout=5000, state="visible")
                    logger.info("Clicking 'Yes' on confirmation popup...")
                    yes_btn.click(force=True)
                    time.sleep(2)
                except Exception as ex:
                    logger.warning(f"Tombol Yes tidak ditemukan setelah menekan Escape: {ex}")
                    
            except Exception as e:
                logger.info(f"No Ganti Password popup found. Continuing... ({e})")
                
            # Tunggu jika masih ada sisa efek loading/mask
            try:
                page.wait_for_selector(".z-modal-mask", state="hidden", timeout=5000)
            except:
                pass
                
            # 5. Navigate Menu
            logger.info("Navigating Menu FMS")
            page.locator("span.z-menu-text", has_text="Finance & Accounting").click(force=True)
            time.sleep(1)
            page.locator("span.z-menu-text", has_text="Bukti Bank").click(force=True)
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
            
            # Extract Nomor Jurnal directly from the form
            try:
                logger.info("Mencoba mengekstrak Nomor Jurnal dari form UI (field readonly)...")
                readonly_inputs = page.locator("input[readonly], input.z-textbox[readonly]")
                for i in range(readonly_inputs.count()):
                    val = readonly_inputs.nth(i).input_value()
                    if val and re.search(r'\d{3,6}/(BBK|GJ|BBM)', val):
                        no_jurnal = val
                        logger.info(f"Berhasil mengekstrak Nomor Jurnal dari form: {no_jurnal}")
                        break
            except Exception as e:
                logger.warning(f"Gagal mengekstrak Nomor Jurnal dari form: {e}")
            
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
            
            # 10. Check checkbox for exact policy with Polling
            logger.info(f"Selecting policy checkbox for {nomor_polis} (with polling)")
            
            max_cari_retries = 10
            endorsement_found = False
            
            for attempt in range(max_cari_retries):
                page.locator("button:visible", has_text="Cari").last.click()
                time.sleep(4)
                
                # Sesuai arahan: tunggu datanya muncul dulu dengan exact no polis yg dicari
                # Kita cari row yang mengandung nomor_polis persis
                target_row = modal.locator("tr.z-listitem", has_text=nomor_polis)
                if target_row.count() == 0:
                    target_row = modal.locator("tr.z-listitem", has_text="/C")
                
                if target_row.count() > 0:
                    # Pastikan baris tersebut benar-benar visible
                    try:
                        target_row.first.wait_for(state="visible", timeout=5000)
                        checkbox = target_row.first.locator(".z-listitem-checkbox, .z-listitem-checkable")
                        if checkbox.count() > 0:
                            endorsement_found = True
                            logger.info(f"Data endorsement ditemukan pada percobaan ke-{attempt + 1}")
                            break
                    except Exception as e:
                        logger.warning(f"Baris ditemukan tapi belum stabil: {e}")
                
                logger.info(f"Percobaan {attempt + 1}/{max_cari_retries}: Data belum muncul secara utuh, menunggu sebelum mencari lagi...")
                time.sleep(3)
            
            if endorsement_found:
                logger.info("Mengeklik checkbox data dan tombol Pilih...")
                time.sleep(2) # Extra wait for DOM stability
                try:
                    # Klik menggunakan Playwright click
                    checkbox = target_row.first.locator(".z-listitem-checkbox, .z-listitem-checkable").first
                    checkbox.hover()
                    time.sleep(1)
                    checkbox.click(force=True)
                    logger.info("Checkbox diklik, menunggu ZK AJAX response...")
                except Exception as e:
                    logger.warning(f"Gagal klik checkbox spesifik, fallback klik baris: {e}")
                    target_row.first.click(force=True)
                
                # Wajib nunggu lama agar state "selected" tersimpan di server ZK
                time.sleep(4)
                
                # Handle popup "Belum ada data yang dipilih" jika muncul pas klik Pilih
                page.locator("button:visible", has_text="Pilih").last.click(force=True)
                time.sleep(3)
                
                # Kalau gagal dan muncul popup "Belum ada data", coba ulang klik
                error_popup = page.locator(".z-messagebox-window:visible", has_text="Belum ada data yang dipilih")
                if error_popup.count() > 0:
                    logger.warning("Server ZK belum menangkap pilihan! Mencoba klik ulang secara JS...")
                    page.locator("button.z-messagebox-button:visible", has_text="OK").last.click(force=True)
                    time.sleep(2)
                    target_row.first.evaluate("node => node.click()")
                    time.sleep(3)
                    page.locator("button:visible", has_text="Pilih").last.click(force=True)
                    time.sleep(3)
            else:
                error_msg = f"Data polis {nomor_polis} tidak ditemukan setelah {max_cari_retries} kali klik Cari!"
                logger.error(error_msg)
                raise Exception(error_msg)
            
            # Tunggu loading mask menghilang dari layar
            try:
                page.wait_for_selector(".z-modal-mask", state="hidden", timeout=10000)
            except:
                pass
            time.sleep(2)
            
            # 11. Delete Ledger row
            # Filter baris yang visible dan ambil yang terakhir (paling atas di tumpukan modal ZK)
            ledger_row = page.locator("tr:visible", has=page.locator("input[value='Ledger']")).last
            
            # Pilih baris data terlebih dahulu (wajib di UAT agar tombol Hapus memunculkan konfirmasi)
            try:
                # Coba cari checkbox/radio di baris ledger dan klik via JS DOM
                checkbox = ledger_row.locator(".z-listitem-checkbox, .z-listitem-checkable, i.z-listitem-icon")
                if checkbox.count() > 0:
                    checkbox.first.click(force=True)
                else:
                    ledger_row.locator("td, .z-listcell").first.click(force=True)
                logger.info("Baris ledger diklik, menunggu ZK...")
                time.sleep(3) # Tunggu AJAX server update status selected
            except Exception as e:
                logger.warning(f"Gagal memilih baris ledger: {e}")
                
            delete_btn = ledger_row.locator("button[title='Hapus']:visible")
            delete_btn.click(force=True)
            
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
            time.sleep(3)
            
            
            # 12. Nominal Kredit / Transaksi
            logger.info("Setting Nominal Kredit")
            try:
                # Ambil value debet
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
                    
                # Clean the nominal string (remove . and convert , to .)
                clean_nominal = nominal_str.replace('.', '').strip()
                logger.info(f"Extracted Debit Nominal: '{nominal_str}', Cleaned: '{clean_nominal}'")
                nominal_str = clean_nominal
                
                # Cari input Nominal Transaksi / Kredit
                # Coba cari berdasarkan form-group atau input decimal
                kredit_input = None
                
                # Coba cari label Nominal Transaksi
                nominal_group = page.locator(".form-group:visible").filter(has_text="Nominal")
                if nominal_group.count() > 0:
                    kredit_input = nominal_group.locator("input:not([readonly])").first
                else:
                    # Fallback ke z-decimalbox terakhir (biasanya kolom nominal)
                    kredit_input = page.locator("input.z-decimalbox:not([readonly]):visible, input.z-doublebox:not([readonly]):visible").last
                
                if kredit_input and kredit_input.count() > 0:
                    kredit_input.fill(nominal_str)
                    time.sleep(1)
                    page.keyboard.press("Enter")
                    time.sleep(1)
                    page.keyboard.press("Tab")
                    time.sleep(3) # Wait for labels to update and balance
                else:
                    # Fallback ke locator lama yang dimodif
                    page.locator("input[type='text']:not([readonly]):visible").last.fill(nominal_str)
                    time.sleep(1)
                    page.keyboard.press("Tab")
                    
            except Exception as e:
                logger.warning(f"Could not set Nominal Kredit: {e}")
                
# 13. Workflow Loop: Submit -> Approve -> Posting
            # 13. Dynamic Workflow Loop: Submit -> Setuju (bisa berulang) -> Posting
            max_workflow_iterations = 10
            for i in range(max_workflow_iterations):
                page.wait_for_load_state("domcontentloaded")
                time.sleep(5)
                # Tunggu loading z-loading hilang jika ada
                try:
                    loading = page.locator(".z-loading")
                    if loading.count() > 0:
                        loading.last.wait_for(state="hidden", timeout=15000)
                except:
                    pass
                time.sleep(2)
                
                # Prioritas 1: Jika tombol Posting sudah muncul, ini adalah tahap terakhir
                step_name = ""
                btn = page.locator("button:visible", has_text="Posting").last
                if btn.count() > 0:
                    step_name = "Posting"
                else:
                    # Prioritas 2: Tombol Submit
                    btn = page.locator("button:visible", has_text="Submit").last
                    if btn.count() > 0:
                        step_name = "Submit"
                    else:
                        # Prioritas 3: Tombol Setuju / Approve (bisa muncul berkali-kali)
                        btn = page.locator("button:visible", has_text=re.compile(r"(Setuju|Approve)", re.IGNORECASE)).last
                        if btn.count() > 0:
                            step_name = "Setuju"
                
                if not step_name:
                    logger.info("Tidak ada tombol workflow (Submit/Setuju/Posting) yang ditemukan. Loop selesai.")
                    break
                    
                logger.info(f"Mengeksekusi workflow step: {step_name} (Iterasi ke-{i+1})")
                
                # Scroll ke elemen jika ada di luar layar
                try:
                    btn.scroll_into_view_if_needed(timeout=2000)
                except:
                    pass
                
                # Isi catatan
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
                    
                # Klik tombol
                btn.click(force=True)
                time.sleep(2)
                
                # Klik Yes
                try:
                    yes_btn = page.locator("button.z-messagebox-button:visible", has_text="Yes").last
                    if yes_btn.count() == 0:
                        yes_btn = page.locator("button:visible", has_text="Yes").last
                    
                    if yes_btn.is_visible(timeout=5000):
                        yes_btn.click(force=True)
                        time.sleep(3)
                except Exception as e:
                    logger.warning(f"Gagal klik Yes setelah {step_name}: {e}")
                
                # Klik OK (dan tangkap nomor jurnal jika ada)
                try:
                    time.sleep(2)
                    ok_btn = page.locator("button.z-messagebox-button:visible", has_text="Ok").last
                    if ok_btn.count() == 0:
                        ok_btn = page.locator("button:visible", has_text="Ok").last
                        
                    if ok_btn.is_visible(timeout=5000):
                        logger.info(f"Clicking Ok on Success popup after {step_name}")
                        try:
                            popup_window = page.locator(".z-messagebox-window, .z-window-highlighted").last
                            if popup_window.count() > 0:
                                popup_text = popup_window.inner_text()
                                match = re.search(r'\d{3,6}/(BBK|GJ|BBM)[-/]\d{2}[-/]\d{2}[-/]\d{2,4}', popup_text)
                                if match:
                                    no_jurnal = match.group(0)
                                    logger.info(f"Berhasil mengekstrak Nomor Jurnal: {no_jurnal}")
                                else:
                                    logger.warning(f"Nomor Jurnal tidak ditemukan dalam text popup: {popup_text}")
                            else:
                                logger.warning("Popup window tidak ditemukan saat mencoba ekstrak no_jurnal")
                        except Exception as ex:
                            logger.error(f"Error saat ekstrak popup text: {ex}")
                            pass
                        ok_btn.click(force=True)
                        time.sleep(2)
                except Exception as e:
                    pass
                
                page.wait_for_load_state("domcontentloaded")
                time.sleep(3)
                
                # Cek error popup
                error_popup = page.locator(".z-window-highlighted, .z-messagebox-window, .z-notification").last
                if error_popup.count() > 0 and error_popup.is_visible(timeout=1000):
                    error_text = error_popup.inner_text()
                    if "berhasil" not in error_text.lower() and "sukses" not in error_text.lower() and "apakah anda yakin" not in error_text.lower():
                        logger.error(f"FMS Popup Error detected after clicking {step_name}: {error_text}")
                        raise Exception(f"FMS Workflow blocked by error popup: {error_text}")
                
                if step_name == "Posting":
                    logger.info("Step Posting berhasil dijalankan. Mengakhiri loop workflow.")
                    break
            
            # Screenshot evidence (Atas dan Bawah)
            evidence_dir = "evidence/fms"
            os.makedirs(evidence_dir, exist_ok=True)
            
            screenshot_path_atas = f"{evidence_dir}/bbk_restitusi_atas_{tc_id}.png"
            screenshot_path_bawah = f"{evidence_dir}/bbk_restitusi_bawah_{tc_id}.png"
            screenshot_paths = []
            
            try:
                # 1. Screenshot Atas (Target Modal if exists)
                window_locator = page.locator(".z-window, .z-window-modal, .z-window-highlighted").first
                if window_locator.is_visible():
                    window_locator.screenshot(path=screenshot_path_atas)
                else:
                    page.screenshot(path=screenshot_path_atas, full_page=True)
                screenshot_paths.append(screenshot_path_atas)
                
                # 2. Scroll ke bawah (Targeting Tutup button or scroll containers)
                try:
                    tutup_btn = page.locator("button:has-text('Tutup')").first
                    if tutup_btn.count() > 0:
                        tutup_btn.scroll_into_view_if_needed()
                        page.wait_for_timeout(1000)
                except:
                    pass
                    
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.evaluate("""
                    var scrollableDivs = document.querySelectorAll('.z-window-content, .z-panel-body, .z-grid-body, .z-listbox-body');
                    for (var i = 0; i < scrollableDivs.length; i++) {
                        scrollableDivs[i].scrollTop = scrollableDivs[i].scrollHeight;
                    }
                """)
                time.sleep(2)
                
                # 3. Screenshot Bawah
                if window_locator.is_visible():
                    window_locator.screenshot(path=screenshot_path_bawah)
                else:
                    page.screenshot(path=screenshot_path_bawah, full_page=True)
                screenshot_paths.append(screenshot_path_bawah)
                
            except Exception as e:
                logger.warning(f"Screenshot failed: {e}")
                
            if evidence_collector and len(screenshot_paths) > 0:
                for idx, path in enumerate(screenshot_paths):
                    label = "FMS BBK Jurnal (Atas)" if idx == 0 else "FMS BBK Jurnal (Bawah)"
                    evidence_collector.add_ui_evidence(tc_id, f"{label} - {nomor_polis}", path)
            
            return no_jurnal
                
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
