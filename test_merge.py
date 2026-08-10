from docx import Document
import copy
doc = Document('collections/TEMPLATE_Defect Report.docx')
template_tbl = doc.tables[0]
doc.add_page_break()
new_tbl = copy.deepcopy(template_tbl._element)
doc._body._element.append(new_tbl)
doc.save('test_merge.docx')
print("Done")
