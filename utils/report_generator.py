import os
import copy
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

def set_table_borders(table):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), 'single')
        border.set(qn('w:sz'), '4')
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), '000000')
        tblBorders.append(border)
    tblPr.append(tblBorders)

def set_cell_background(cell, color_hex):
    from docx.oxml.shared import OxmlElement
    from docx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def add_page_number(run):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    fldChar1 = OxmlElement('w:fldChar')
    fldChar1.set(qn('w:fldCharType'), 'begin')
    instrText = OxmlElement('w:instrText')
    instrText.set(qn('xml:space'), 'preserve')
    instrText.text = "PAGE"
    fldChar2 = OxmlElement('w:fldChar')
    fldChar2.set(qn('w:fldCharType'), 'separate')
    t = OxmlElement('w:t')
    t.text = "1"
    fldChar3 = OxmlElement('w:fldChar')
    fldChar3.set(qn('w:fldCharType'), 'end')
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(t)
    run._r.append(fldChar3)

class ReportGenerator:
    def __init__(self, template_dir="templates"):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def _filter_db_results(self, evidences: dict) -> dict:
        evidences_copy = copy.deepcopy(evidences)
        allowed_cols = {
            'nomor_transaksi', 'status_akseptasi', 'tanggal_lahir', 
            'tanggal_rencana_realisasi', 'tanggal_akhir_asuransi', 
            'tenor', 'uang_pertanggungan', 'nomor_loan',
            'ktp', 'id_debitur', 'nilai_pertanggungan', 'nama_debitur', 'Validasi DB', 'Response API', 'Status Code', 'Status Akseptasi',
            'kode_bank', 'jenis_covering', 'jangka_waktu', 'nomor_rekening_pinjaman', 'nomor_perjanjian_kredit', 'tanggal_mulai_covering', 'premi',
            'id_sertifikat', 'no_sertifikat', 'tgl_sertifikat', 'url_download_sertifikat', 'is_polis_sent'
        }
        for tc_id, data in evidences_copy.items():
            for db in data.get('db', []):
                if db.get('result') and isinstance(db['result'], list) and len(db['result']) > 0:
                    if isinstance(db['result'][0], dict):
                        new_results = []
                        for row in db['result']:
                            filtered_row = {k: v for k, v in row.items() if str(k).lower() in allowed_cols}
                            new_results.append(filtered_row if filtered_row else row)
                        db['result'] = new_results
        return evidences_copy

    def generate_html(self, evidences: dict, output_file: str):
        filtered_evidences = self._filter_db_results(evidences)
        template = self.env.get_template("report_template.html")
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_out = template.render(
            evidences=filtered_evidences,
            current_date=current_date
        )
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_out)
        return html_out

    def generate_pdf(self, evidences: dict, output_file: str):
        html_file = output_file.replace(".pdf", ".html")
        self.generate_html(evidences, html_file)
        
        try:
            from weasyprint import HTML
            HTML(html_file).write_pdf(output_file)
            print(f"PDF generated successfully: {output_file}")
        except ImportError:
            print("WeasyPrint is not installed. Skipping PDF generation, HTML saved instead.")
        except Exception as e:
            print(f"Failed to generate PDF: {e}")

    def generate_docx(self, evidences: dict, output_file: str):
        filtered_evidences = self._filter_db_results(evidences)
        try:
            from docx import Document
            from docx.shared import Pt, RGBColor, Inches
            from docx.enum.table import WD_TABLE_ALIGNMENT
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            import json
            
            # Use base_template
            doc = Document('collections/base_template.docx')
            
            # Try to get normal style, fallback if issue
            try:
                style = doc.styles['Normal']
                font = style.font
                font.name = 'Arial'
                font.size = Pt(10)
            except:
                pass
            
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_date_cover = datetime.now().strftime("%d/%m/%Y")
            
            # Set margins to prevent overlapping with footer
            from docx.shared import Inches
            for section in doc.sections:
                section.bottom_margin = Inches(1.5)

            for tc_id, data in filtered_evidences.items():
                doc.add_page_break()
                
                # Info Table (Plain without blue backgrounds)
                table = doc.add_table(rows=5, cols=2)
                try:
                    table.style = 'Table Grid'
                except KeyError:
                    set_table_borders(table)
                table.allow_autofit = False
                table.columns[0].width = Inches(2.0)
                table.columns[1].width = Inches(4.5)
                
                rows = [
                    ("Test Case Id", tc_id),
                    ("Test Case Name", data["tc_name"]),
                    ("Date", current_date),
                    ("Status", data["status"]),
                    ("Expected Result", data["expected_result"])
                ]
                
                for i, (label, val) in enumerate(rows):
                    cell_label = table.cell(i, 0)
                    cell_label.text = label
                    run_label = cell_label.paragraphs[0].runs[0]
                    run_label.bold = True
                    run_label.font.color.rgb = RGBColor(255, 255, 255)
                    set_cell_background(cell_label, '17375E')
                    
                    cell_val = table.cell(i, 1)
                    if label == "Expected Result" and val:
                        # Properly render newlines in python-docx
                        cell_val.text = ""
                        for line in str(val).split('\n'):
                            if not cell_val.paragraphs:
                                p = cell_val.add_paragraph(line)
                            else:
                                if not cell_val.paragraphs[0].text:
                                    cell_val.paragraphs[0].text = line
                                else:
                                    cell_val.add_paragraph(line)
                    else:
                        cell_val.text = str(val)
                    if label == "Status":
                        run = cell_val.paragraphs[0].runs[0]
                        run.bold = True
                        if val.lower() == 'passed':
                            run.font.color.rgb = RGBColor(0, 128, 0)
                        else:
                            run.font.color.rgb = RGBColor(255, 0, 0)
                
                precondition = data.get("precondition", "1. Buka Postman\n2. Set request ke POST...")
                doc.add_paragraph(f"\nPrecondition:\n{precondition}")
                
                doc.add_paragraph()
                
                test_data_str = ""
                for api in data.get("api", []):
                    payload = api.get("request_payload", {})
                    if "nomor_transaksi" in payload and f"nomor_transaksi: {payload['nomor_transaksi']}" not in test_data_str:
                        test_data_str += f"nomor_transaksi: {payload['nomor_transaksi']}\n"
                    if "nomor_loan" in payload and f"nomor_loan: {payload['nomor_loan']}" not in test_data_str:
                        test_data_str += f"nomor_loan: {payload['nomor_loan']}\n"
                    if "ktp" in payload and f"ktp: {payload['ktp']}" not in test_data_str:
                        test_data_str += f"ktp: {payload['ktp']}\n"
                
                if not test_data_str and data.get("api"):
                    payload = data["api"][0].get("request_payload", {})
                    if payload:
                        test_data_str = json.dumps(payload, indent=2)

                if test_data_str:
                    from docx.shared import Pt
                    p_td = doc.add_paragraph(f"Test Data:\n{test_data_str.strip()}")
                    p_td.paragraph_format.space_before = Pt(12)
                    p_td.paragraph_format.space_after = Pt(12)
                
                step_counter = 1
                for api in data["api"]:
                    endpoint_url = api.get('url', '')
                    endpoint_name = "API"
                    if "draft-akseptasi" in endpoint_url: endpoint_name = "Draft Akseptasi"
                    elif "inquiry" in endpoint_url: endpoint_name = "Inquiry Loan"
                    elif "otorisasi" in endpoint_url: endpoint_name = "Otorisasi"
                    elif "payment" in endpoint_url or "pembayaran" in endpoint_url: endpoint_name = "Payment/Pembayaran"
                    elif "batal" in endpoint_url or "cancel" in endpoint_url: endpoint_name = "Pembatalan"
                    
                    p_step = doc.add_paragraph(f"\n[Test_Step_{step_counter}]: Hit API {endpoint_name} ({api['method']} {endpoint_url})", style='Heading 3')
                    p_step.paragraph_format.space_before = Pt(14)
                    p_step.paragraph_format.space_after = Pt(6)
                    
                    api_table = doc.add_table(rows=2, cols=2)
                    try:
                        api_table.style = 'Table Grid'
                    except KeyError:
                        set_table_borders(api_table)
                    api_table.allow_autofit = False
                    api_table.columns[0].width = Inches(3.25)
                    api_table.columns[1].width = Inches(3.25)
                    
                    req_cell = api_table.cell(0, 0)
                    req_cell.text = "Request"
                    req_run = req_cell.paragraphs[0].runs[0]
                    req_run.bold = True
                    req_run.font.color.rgb = RGBColor(255, 255, 255)
                    set_cell_background(req_cell, '17375E')
                    
                    res_cell = api_table.cell(0, 1)
                    res_cell.text = "Response"
                    res_run = res_cell.paragraphs[0].runs[0]
                    res_run.bold = True
                    res_run.font.color.rgb = RGBColor(255, 255, 255)
                    set_cell_background(res_cell, '17375E')
                    
                    req_text = json.dumps(api['request_payload'], indent=2)
                    res_text = json.dumps(api['response_json'], indent=2)
                    
                    api_table.cell(1, 0).text = req_text
                    api_table.cell(1, 1).text = res_text
                    
                    # Only apply Courier New to row 1 (the content)
                    for cell in api_table.rows[1].cells:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.name = 'Courier New'
                                run.font.size = Pt(8)
                    step_counter += 1
                    
                for db in data["db"]:
                    p_db = doc.add_paragraph(f"\n[Test_Step_{step_counter}]: DB Validation", style='Heading 3')
                    p_db.paragraph_format.space_before = Pt(14)
                    p_db.paragraph_format.space_after = Pt(6)
                    doc.add_paragraph(f"Query: {db['query']}")
                    
                    if db['result'] and len(db['result']) > 0:
                        keys = list(db['result'][0].keys()) if isinstance(db['result'][0], dict) else range(len(db['result'][0]))
                        
                        max_cols = 5
                        chunks = [keys[i:i + max_cols] for i in range(0, len(keys), max_cols)]
                        
                        for chunk_idx, chunk_keys in enumerate(chunks):
                            if chunk_idx > 0:
                                doc.add_paragraph() # Spacing between tables
                            
                            db_table = doc.add_table(rows=1, cols=len(chunk_keys))
                            try:
                                db_table.style = 'Table Grid'
                            except KeyError:
                                set_table_borders(db_table)
                            db_table.allow_autofit = True
                            
                            for col_idx, key in enumerate(chunk_keys):
                                head_cell = db_table.cell(0, col_idx)
                                head_cell.text = str(key)
                                head_run = head_cell.paragraphs[0].runs[0]
                                head_run.bold = True
                                head_run.font.color.rgb = RGBColor(255, 255, 255)
                                set_cell_background(head_cell, '17375E')
                                
                            for row in db['result']:
                                row_cells = db_table.add_row().cells
                                for col_idx, key in enumerate(chunk_keys):
                                    val = row[key] if isinstance(row, dict) else row[col_idx]
                                    row_cells[col_idx].text = str(val)
                    else:
                        doc.add_paragraph("No records found.")
                        
                    step_counter += 1
                    
                if "epolis" in data:
                    epolis = data["epolis"]
                    p_epolis = doc.add_paragraph(f"\n[Test_Step_{step_counter}]: Pengecekan Scan QR & Lampiran E-Polis", style='Heading 3')
                    p_epolis.paragraph_format.space_before = Pt(14)
                    p_epolis.paragraph_format.space_after = Pt(6)
                
                    p_qr = doc.add_paragraph()
                    p_qr.add_run("Terjemahan QR Code:\n").bold = True
                    p_qr.add_run(epolis.get("qr_result", "N/A"))
                
                    from docx.shared import Inches
                    for img_path in epolis.get("image_paths", []):
                        try:
                            doc.add_picture(img_path, width=Inches(5.0))
                            doc.add_paragraph() # Spacing between pages
                        except Exception as e:
                            doc.add_paragraph(f"[Gagal melampirkan gambar E-Polis: {e}]")
                        
                    step_counter += 1
                
                if "ui" in data:
                    p_ui = doc.add_paragraph(f"\n[Test_Step_{step_counter}]: Pengecekan UI (ACS/FMS)", style='Heading 3')
                    p_ui.paragraph_format.space_before = Pt(14)
                    p_ui.paragraph_format.space_after = Pt(6)
                    from docx.shared import Inches
                    for ui_ev in data["ui"]:
                        sys_name = ui_ev.get("system_name", "System")
                        img_path = ui_ev.get("screenshot_path", "")
                    
                        p_sys = doc.add_paragraph()
                        p_sys.add_run(f"System: {sys_name}\n").bold = True
                    
                        try:
                            doc.add_picture(img_path, width=Inches(6.0))
                            doc.add_paragraph()
                        except Exception as e:
                            doc.add_paragraph(f"[Gagal melampirkan screenshot {sys_name}: {e}]")
                        
                    step_counter += 1
                    
                if "premi_validation" in data:
                    pv = data["premi_validation"]
                    p_pv = doc.add_paragraph(f"\n[Test_Step_{step_counter}]: Tabel Validasi Nilai Premi", style='Heading 3')
                    p_pv.paragraph_format.space_before = Pt(14)
                    p_pv.paragraph_format.space_after = Pt(6)
                    
                    pv_table = doc.add_table(rows=2, cols=4)
                    try:
                        pv_table.style = 'Table Grid'
                    except KeyError:
                        set_table_borders(pv_table)
                    pv_table.allow_autofit = True
                    
                    headers = ["Response Postman (API)", "Database", "UI ACS", "Status"]
                    for idx, h in enumerate(headers):
                        h_cell = pv_table.cell(0, idx)
                        h_cell.text = h
                        h_run = h_cell.paragraphs[0].runs[0]
                        h_run.bold = True
                        h_run.font.color.rgb = RGBColor(255, 255, 255)
                        set_cell_background(h_cell, '17375E')
                    
                    vals = [f"Rp {pv['api']:,.2f}", f"Rp {pv['db']:,.2f}", f"Rp {pv['acs']:,.2f}", pv['status']]
                    for idx, v in enumerate(vals):
                        v_cell = pv_table.cell(1, idx)
                        v_cell.text = v
                        if idx == 3:
                            v_run = v_cell.paragraphs[0].runs[0]
                            v_run.bold = True
                            if pv['status'] == "Passed":
                                v_run.font.color.rgb = RGBColor(0, 128, 0)
                            else:
                                v_run.font.color.rgb = RGBColor(255, 0, 0)
                                
                    step_counter += 1
            
            # Setup Page Number in Footer
            from docx.oxml import OxmlElement
            from docx.oxml.ns import qn
            
            def setup_footer(footer_obj):
                # Clear any existing junk from footer
                for p in footer_obj.paragraphs:
                    p.text = ""
                    pPr = p._p.get_or_add_pPr()
                    pBdr = pPr.find(qn('w:pBdr'))
                    if pBdr is not None:
                        pPr.remove(pBdr)
                for t in footer_obj.tables:
                    t._element.getparent().remove(t._element)
                    
                # Create a 1-column small box on the right for page number
                footer_table = footer_obj.add_table(rows=1, cols=1, width=Inches(0.5))
                footer_table.alignment = WD_TABLE_ALIGNMENT.RIGHT
                footer_table.autofit = False
                footer_table.columns[0].width = Inches(0.5)
                
                # Make the table borders invisible just in case
                tblPr = footer_table._element.tblPr
                
                cell = footer_table.cell(0, 0)
                set_cell_background(cell, '17375E')
                
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run()
                run.font.size = Pt(11)
                run.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                add_page_number(run)

            for section in doc.sections:
                # Aktifkan pengaturan 'Different First Page' agar cover beda dengan isinya
                section.different_first_page_header_footer = True
                
                # Bersihkan footer di halaman pertama (Cover) agar tidak ada nomor halaman
                first_footer = section.first_page_footer
                for p in first_footer.paragraphs:
                    p.text = ""
                for t in first_footer.tables:
                    t._element.getparent().remove(t._element)
                    
                # Pasang kotak penomoran biru hanya untuk halaman utama & genap (mulai halaman 2)
                setup_footer(section.footer)
                setup_footer(section.even_page_footer)

            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            doc.save(output_file)
            print(f"DOCX generated successfully: {output_file}")
        except Exception as e:
            print(f"Failed to generate DOCX: {e}")

    def generate_excel(self, evidences: dict, output_file: str):
        import os
        import json
        from openpyxl import load_workbook
        from openpyxl.styles import Alignment, Font

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        try:
            wb = load_workbook('collections/test_script.xlsx')
            ws = wb.active
            
            for row in range(4, ws.max_row + 1):
                tc_id = ws.cell(row=row, column=4).value
                if not tc_id or not isinstance(tc_id, str) or not tc_id.startswith("TC-"):
                    continue
                    
                if tc_id in evidences:
                    data = evidences[tc_id]
                    
                    if data.get("api") and len(data["api"]) > 0:
                        actual_json = data["api"][-1].get("response_json", {})
                        if actual_json:
                            # Use status to determine DB message for Actual Result
                            expected = data.get("expected_result", "")
                            if "tidak kerecord" in expected.lower():
                                db_msg = "2. data tidak kerecord di DB"
                            else:
                                db_msg = "2. data DB sesuai dengan request postman"
                                
                            ws.cell(row=row, column=10).value = "1. Response API:\n" + json.dumps(actual_json, indent=2) + "\n\n" + db_msg
                            ws.cell(row=row, column=10).alignment = Alignment(wrap_text=True, vertical="top")
                            
                    ws.cell(row=row, column=11).value = data.get("status", "Failed")
                    
                    test_data_str = ""
                    for api in data.get("api", []):
                        payload = api.get("request_payload", {})
                        if "nomor_transaksi" in payload and f"nomor_transaksi: {payload['nomor_transaksi']}" not in test_data_str:
                            test_data_str += f"nomor_transaksi: {payload['nomor_transaksi']}\n"
                        if "nomor_loan" in payload and f"nomor_loan: {payload['nomor_loan']}" not in test_data_str:
                            test_data_str += f"nomor_loan: {payload['nomor_loan']}\n"
                        if "ktp" in payload and f"ktp: {payload['ktp']}" not in test_data_str:
                            test_data_str += f"ktp: {payload['ktp']}\n"
                    if test_data_str:
                        ws.cell(row=row, column=9).value = test_data_str.strip()
                        ws.cell(row=row, column=9).alignment = Alignment(wrap_text=True, vertical="top")
                        
                    ws.cell(row=row, column=13).value = "Fathur"
                    ws.cell(row=row, column=14).value = datetime.now().strftime("%d-%b-%Y")

            # Fill down Stream and Nama Modul
            last_stream = None
            last_modul = None
            for row in range(4, ws.max_row + 1):
                stream_val = ws.cell(row=row, column=2).value
                modul_val = ws.cell(row=row, column=3).value
                if stream_val: last_stream = stream_val
                elif last_stream: ws.cell(row=row, column=2).value = last_stream
                if modul_val: last_modul = modul_val
                elif last_modul: ws.cell(row=row, column=3).value = last_modul

            # Merge Title A1 to N2, center, wrap text, size 20, bold
            # Unmerge any existing ranges to prevent Excel corruption
            for range_str in list(ws.merged_cells.ranges):
                if "A1" in str(range_str):
                    try:
                        ws.unmerge_cells(str(range_str))
                    except Exception:
                        pass
            try:
                ws.merge_cells("A1:N2")
            except Exception:
                pass
            title_cell = ws.cell(row=1, column=1)
            title_cell.font = Font(size=20, bold=True)
            title_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Format Header Row (Row 3): Blue background, White text, Bold
            from openpyxl.styles import PatternFill
            header_fill = PatternFill(start_color="003366", end_color="003366", fill_type="solid")
            header_font = Font(color="FFFFFF", bold=True)
            for col in range(1, ws.max_column + 1):
                header_cell = ws.cell(row=3, column=col)
                header_cell.fill = header_fill
                header_cell.font = header_font
                header_cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Apply Full Border to the table (Row 3 to Max Row)
            from openpyxl.styles import Border, Side
            thin_border = Border(left=Side(style='thin'), 
                                 right=Side(style='thin'), 
                                 top=Side(style='thin'), 
                                 bottom=Side(style='thin'))
            
            for r in ws.iter_rows(min_row=3, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                for cell in r:
                    cell.border = thin_border

            # Save the final file
            wb.save(output_file)
            wb.save('collections/test_script.xlsx')
            
            print(f"Excel report generated successfully: {output_file}")
        except Exception as e:
            import traceback
            print(f"Failed to generate Excel report: {e}\n{traceback.format_exc()}")

report_generator = ReportGenerator()
