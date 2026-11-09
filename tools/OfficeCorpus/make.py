# TESTING ONLY (never shipped; D-136). Builds the Word/Excel corpus for the Docs 2.0.0 / Sheets 2.0.2 move, with the values each
# file truly holds written beside it (expected.json), so the viewer's output can be checked against the file.
import zipfile, json, os, sys, datetime, io, struct, zlib
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
expected = {}

CT = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{sheets}<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>'
RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'
STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/></numFmts><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFC00000"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFF2CC"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/><xf numFmtId="14" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" wrapText="1"/></xf><xf numFmtId="164" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/></cellXfs></styleSheet>'''

def xlsx(name, sheets, date1904=False, shared=()):
    """sheets: list of (sheetname, hidden, rows_xml, extra_after_sheetData, sheetViews)"""
    ov = ''.join(f'<Override PartName="/xl/worksheets/sheet{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(len(sheets)))
    wb = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' + (f'<workbookPr date1904="1"/>' if date1904 else '') + '<sheets>' + ''.join(f'<sheet name="{s[0]}" sheetId="{i+1}" r:id="rId{i+1}"' + (' state="hidden"' if s[1] else '') + '/>' for i, s in enumerate(sheets)) + '</sheets></workbook>'
    wbrels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i+1}.xml"/>' for i in range(len(sheets))) + f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/><Relationship Id="rId{len(sheets)+2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>'
    def esc(t): return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    sst = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="%d" uniqueCount="%d">' % (len(shared), len(shared)) + ''.join(f'<si><t xml:space="preserve">{esc(t)}</t></si>' for t in shared) + '</sst>'
    with zipfile.ZipFile(os.path.join(out, name), 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', CT.format(sheets=ov)); z.writestr('_rels/.rels', RELS)
        z.writestr('xl/workbook.xml', wb); z.writestr('xl/_rels/workbook.xml.rels', wbrels)
        z.writestr('xl/sharedStrings.xml', sst); z.writestr('xl/styles.xml', STYLES)
        for i, (sn, hid, rows, extra, views) in enumerate(sheets):
            z.writestr(f'xl/worksheets/sheet{i+1}.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + views + '<sheetData>' + rows + '</sheetData>' + extra + '</worksheet>')

# 1. values.xlsx — every value kind, with what the file holds
shared = ['Ward', '  leading spaces', 'trailing spaces  ', 'double  space inside', 'தமிழ் உரை', 'Line1\nLine2', 'A&B <tag>', '']
rows = ''.join([
 '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s" s="2"><v>4</v></c><c r="C1" t="inlineStr"><is><t xml:space="preserve"> inline  text </t></is></c></row>',
 '<row r="2"><c r="A2" t="s"><v>1</v></c><c r="B2" t="s"><v>2</v></c><c r="C2" t="s"><v>3</v></c><c r="D2" t="s"><v>5</v></c><c r="E2" t="s"><v>6</v></c></row>',
 '<row r="3"><c r="A3"><v>42</v></c><c r="B3"><v>-7.25</v></c><c r="C3"><v>0.1</v></c><c r="D3"><v>1234567890123</v></c><c r="E3"><v>1.5E-7</v></c><c r="F3"><v>3.14159265358979</v></c></row>',
 '<row r="4"><c r="A4"><f>A3*2</f><v>84</v></c><c r="B4" t="str"><f>"Total: "&amp;A3</f><v>Total: 42</v></c><c r="C4"><f>SUM(A3:B3)</f><v>34.75</v></c><c r="D4" t="b"><f>A3&gt;10</f><v>1</v></c></row>',
 '<row r="5"><c r="A5" t="b"><v>1</v></c><c r="B5" t="b"><v>0</v></c><c r="C5" t="e"><v>#DIV/0!</v></c><c r="D5" t="e"><f>1/0</f><v>#DIV/0!</v></c></row>',
 '<row r="6"><c r="A6" s="1"><v>45601</v></c><c r="B6" s="3"><v>45601.5</v></c><c r="C6" s="1"><v>1</v></c><c r="D6" s="1"><v>59</v></c><c r="E6" s="1"><v>61</v></c></row>',
 '<row r="8"><c r="H8"><v>8</v></c></row>',
])
views = '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" xSplit="1" topLeftCell="B2" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>'
cols = '<cols><col min="1" max="1" width="24" customWidth="1"/><col min="3" max="3" width="30.5" customWidth="1"/></cols>'
xlsx('values.xlsx', [('Values', False, rows, '', views.replace('<sheetData>', '') ), ('Hidden one', True, '<row r="1"><c r="A1"><v>1</v></c></row>', '', ''), ('Empty', False, '', '', '')], shared=shared)
# cols must precede sheetData: rewrite sheet1 with cols
with zipfile.ZipFile(os.path.join(out, 'values.xlsx')) as z: parts = {n: z.read(n) for n in z.namelist()}
s1 = parts['xl/worksheets/sheet1.xml'].decode().replace('<sheetData>', cols + '<sheetData>')
parts['xl/worksheets/sheet1.xml'] = s1.encode()
with zipfile.ZipFile(os.path.join(out, 'values.xlsx'), 'w', zipfile.ZIP_DEFLATED) as z:
    for n, b in parts.items(): z.writestr(n, b)
expected['values.xlsx'] = {
  'note': 'cell -> what the file holds (shared/inline strings verbatim; numbers as stored; formula cells: their stored result; booleans; errors)',
  'strings': {'A1': 'Ward', 'B1': 'தமிழ் உரை', 'C1': ' inline  text ', 'A2': '  leading spaces', 'B2': 'trailing spaces  ', 'C2': 'double  space inside', 'D2': 'Line1\nLine2', 'E2': 'A&B <tag>', 'B4': 'Total: 42'},
  'numbers': {'A3': 42, 'B3': -7.25, 'C3': 0.1, 'D3': 1234567890123, 'E3': 1.5e-7, 'F3': 3.14159265358979, 'A4': 84, 'C4': 34.75},
  'booleans': {'A5': True, 'B5': False, 'D4': True},
  'errors': {'C5': '#DIV/0!', 'D5': '#DIV/0!'},
  'dates_1900': {'A6': '2024-11-05', 'B6': '2024-11-05 12:00', 'C6': '1900-01-01', 'D6': '1900-02-28', 'E6': '1900-03-01'},
}
# 2. dates1904.xlsx — the 1904 date system (Mac Excel)
xlsx('dates1904.xlsx', [('Dates', False, '<row r="1"><c r="A1" s="1"><v>0</v></c><c r="B1" s="1"><v>44139</v></c><c r="C1"><v>44139</v></c></row>', '', '')], date1904=True)
expected['dates1904.xlsx'] = {'dates_1904': {'A1': '1904-01-01', 'B1': '2024-11-05'}, 'numbers': {'C1': 44139}}

# 3. realistic.xlsx via openpyxl (a typical census sheet)
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Census'
hdr = ['Bed', 'Patient', 'Admitted', 'Charges (₹)', 'Paid', 'Notes']
ws.append(hdr)
for c in ws[1]: c.font = Font(bold=True); c.fill = PatternFill('solid', fgColor='DDEBF7')
import random; random.seed(7)
real = {}
for i in range(2, 202):
    row = [f'B-{i-1:03d}', random.choice(['Arun  Kumar', 'Lakshmi', ' Ravi', 'Meena ', 'Dr. S. Iyer']), datetime.date(2026, 10, 1) + datetime.timedelta(days=i % 30), round(random.uniform(500, 250000), 2), random.choice([True, False]), random.choice(['', 'review', 'NPO after 10 pm', 'ICU → ward'])]
    ws.append(row)
ws['G1'] = 'Total'; ws['G2'] = '=SUM(D2:D201)'
ws.freeze_panes = 'B2'; ws.column_dimensions['B'].width = 22
ws2 = wb.create_sheet('Summary'); ws2['A1'] = 'Rows'; ws2['B1'] = 200; ws2['A2'] = 'Ratio'; ws2['B2'] = 0.333333333333333
wb.save(os.path.join(out, 'realistic.xlsx'))
# What the file holds, read back by openpyxl (not by Chuvadi): every cell with a value, as the viewer should show it.
rb = openpyxl.load_workbook(os.path.join(out, 'realistic.xlsx'), data_only=True)
cells = {}
for si, rws in enumerate(rb.worksheets):
    for row in rws.iter_rows():
        for c in row:
            v = c.value
            if v is None: continue
            if isinstance(v, bool): t = {'kind': 'text', 'value': 'TRUE' if v else 'FALSE'}
            elif isinstance(v, datetime.datetime): t = {'kind': 'text', 'value': v.strftime('%Y-%m-%d') if v.time() == datetime.time() else v.strftime('%Y-%m-%d %H:%M')}
            elif isinstance(v, (int, float)): t = {'kind': 'number', 'value': v}
            else: t = {'kind': 'text', 'value': v}
            cells[f'{si}!{c.coordinate}'] = t
expected['realistic.xlsx'] = {'note': 'every cell with a value, read back by openpyxl; G2 is a formula saved with no stored result, so it holds nothing', 'cells': cells, 'empty': ['0!G2']}

# 4. Word documents via python-docx
import docx
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.section import WD_ORIENT
d = docx.Document()
d.add_paragraph('Discharge summary', style='Title')
d.add_heading('Patient details', level=1)
p = d.add_paragraph(); r = p.add_run('Name:'); r.bold = True; p.add_run('\tArun  Shiva'); 
p = d.add_paragraph('Line one'); p.runs[0].add_break(); p.add_run('Line two after a break')
p = d.add_paragraph(); r = p.add_run('Red 14pt Georgia'); r.font.color.rgb = RGBColor(0xC0, 0, 0); r.font.size = Pt(14); r.font.name = 'Georgia'
p = d.add_paragraph(); p.add_run('italic').italic = True; p.add_run(' · '); p.add_run('underline').underline = True; p.add_run(' · '); s = p.add_run('struck'); s.font.strike = True
d.add_paragraph('  two leading spaces and  double  spaces  ')
d.add_paragraph('தமிழ்: நோயாளி விவரங்கள்')
p = d.add_paragraph('Centred'); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
d.add_heading('Medications', level=2)
for m in ['Paracetamol 500 mg', 'Pantoprazole 40 mg']: d.add_paragraph(m, style='List Bullet')
for m in ['Review in 7 days', 'CBC before review']: d.add_paragraph(m, style='List Number')
d.add_paragraph('Quoted advice', style='Quote')
t = d.add_table(rows=3, cols=3); t.style = 'Table Grid'
for i, rowv in enumerate([['Test', 'Result', 'Range'], ['Hb', '11.2', '12–16'], ['WBC', '9 800', '4 000–11 000']]):
    for j, v in enumerate(rowv): t.cell(i, j).text = v
d.add_heading('Third level', level=3)
d.sections[0].header.paragraphs[0].text = 'Apulki Medical Center · Confidential'
d.sections[0].footer.paragraphs[0].text = 'Page footer text'
d.save(os.path.join(out, 'discharge.docx'))
expected['discharge.docx'] = {'paragraph_texts_in_order': ['Discharge summary', 'Patient details', 'Name:\tArun  Shiva', 'Line one\nLine two after a break', 'Red 14pt Georgia', 'italic · underline · struck', '  two leading spaces and  double  spaces  ', 'தமிழ்: நோயாளி விவரங்கள்', 'Centred', 'Medications', 'Paracetamol 500 mg', 'Pantoprazole 40 mg', 'Review in 7 days', 'CBC before review', 'Quoted advice', 'Third level'],
  'table': [['Test', 'Result', 'Range'], ['Hb', '11.2', '12–16'], ['WBC', '9 800', '4 000–11 000']], 'header': 'Apulki Medical Center · Confidential', 'footer': 'Page footer text'}
d = docx.Document(); s = d.sections[0]; s.orientation = WD_ORIENT.LANDSCAPE; s.page_width, s.page_height = s.page_height, s.page_width
d.add_heading('Landscape report', level=1); d.add_paragraph('Wide table follows.')
# a tiny PNG image
def png():
    raw = b''.join(b'\x00' + bytes([200, 60, 40]) * 4 for _ in range(4))
    def chunk(t, b): return struct.pack('>I', len(b)) + t + b + struct.pack('>I', zlib.crc32(t + b) & 0xffffffff)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 4, 4, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')
d.add_picture(io.BytesIO(png()))
d.save(os.path.join(out, 'landscape.docx'))
expected['landscape.docx'] = {'paragraph_texts_in_order': ['Landscape report', 'Wide table follows.'], 'landscape': True, 'images': 1}
json.dump(expected, open(os.path.join(out, 'expected.json'), 'w'), ensure_ascii=False, indent=1)
print('\n'.join(sorted(f for f in os.listdir(out))))
