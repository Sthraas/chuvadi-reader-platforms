# TESTING ONLY (D-161): formats.xlsx, one row per number-format case (label in A, value in B), written straight as XML
# so the stored values are known. Usage: python3 make_formats.py ../../tests/ChuvadiReader.Tests/Fixtures/Office/formats.xlsx
import zipfile, sys
cases = [
 # (label, value-xml, type, numFmtId, custom code or None)
 ("General int", "1234567", "n", 0, None),
 ("General long decimal", "3.14159265358979", "n", 0, None),
 ("General 12-digit", "123456789012", "n", 0, None),
 ("General huge", "1.23456789012345E+20", "n", 0, None),
 ("0.00 (2)", "1234.5", "n", 2, None),
 ("#,##0 (3)", "1234567", "n", 3, None),
 ("#,##0.00 (4)", "-1234567.891", "n", 4, None),
 ("currency id 5", "1234.5", "n", 5, None),
 ("currency id 6 neg", "-1234.5", "n", 6, None),
 ("currency id 7", "1234.5", "n", 7, None),
 ("currency id 8 neg", "-1234.5", "n", 8, None),
 ("0% (9)", "0.256", "n", 9, None),
 ("0.00% (10)", "0.256", "n", 10, None),
 ("0.00E+00 (11)", "123456", "n", 11, None),
 ("# ?/? (12)", "1.25", "n", 12, None),
 ("date 14", "45000", "n", 14, None),
 ("d-mmm-yy 15", "45000", "n", 15, None),
 ("h:mm AM/PM 18", "0.75", "n", 18, None),
 ("h:mm:ss 21", "0.5104166", "n", 21, None),
 ("m/d/yy h:mm 22", "45000.75", "n", 22, None),
 ("accounting 41", "1234.5", "n", 41, None),
 ("accounting 42", "-1234.5", "n", 42, None),
 ("accounting 43", "0", "n", 43, None),
 ("accounting 44", "1234.5", "n", 44, None),
 ("[h]:mm:ss 46", "1.5", "n", 46, None),
 ("text @ 49", "007", "s", 49, None),
 ("rupee custom", "1234567.5", "n", 164, "[$₹-4009] #,##0.00"),
 ("en-IN grouping custom", "12345678", "n", 165, "#,##,##0"),
 ("4 sections pos", "5", "n", 166, "0.0;[Red](0.0);\"zero\";\"txt:\"@"),
 ("4 sections neg", "-5", "n", 166, None),
 ("4 sections zero", "0", "n", 166, None),
 ("4 sections text", "abc", "s", 166, None),
 ("condition [>100]", "150", "n", 167, "[>100][Blue]\"big \"0;[<=100]\"small \"0"),
 ("color10", "42", "n", 168, "[Color10]0"),
 ("fill *", "12", "n", 169, "_(\"$\"* #,##0.00_)"),
 ("dddd dd mmmm yyyy", "45000", "n", 170, "dddd, dd mmmm yyyy"),
 ("system long date F800", "45000", "n", 171, "[$-F800]dddd\\,\\ mmmm\\ dd\\,\\ yyyy"),
 ("system time F400", "0.75", "n", 172, "[$-F400]h:mm:ss\\ AM/PM"),
 ("DBNum1", "123", "n", 173, "[DBNum1]General"),
 ("buddhist B2", "45000", "n", 174, "[$-th-TH,107]d/m/yyyy"),
 ("hijri", "45000", "n", 175, "[$-2000000]B2dd/mm/yyyy"),
 ("fraction ??/100", "0.37", "n", 176, "# ??/100"),
 ("scale ,", "1234567", "n", 177, "#,##0,\"K\""),
 ("ss.000", "0.0000123", "n", 178, "mm:ss.000"),
 ("date serial 60", "60", "n", 14, None),
 ("date serial 1", "1", "n", 14, None),
 ("bool", "1", "b", 0, None),
 ("error", "#DIV/0!", "e", 0, None),
 ("date in de locale tag", "45000", "n", 179, "[$-407]dddd, d. mmmm yyyy"),
 ("dd/mm/yyyy", "45000", "n", 180, "dd/mm/yyyy"),
 ("percent text", "0.5", "n", 181, "0%\" done\""),
 ("negative red no sign", "-3", "n", 182, "0;[Red]0"),
]
customs = {}
for c in cases:
    if c[4]: customs[c[3]] = c[4]
numfmts = "".join(f'<numFmt numFmtId="{i}" formatCode="{code.replace("&","&amp;").replace(chr(34),"&quot;").replace("<","&lt;").replace(">","&gt;")}"/>' for i, code in customs.items())
ids = sorted({c[3] for c in cases})
xf_index = {i: n for n, i in enumerate(ids)}
xfs = "".join(f'<xf numFmtId="{i}" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>' for i in ids)
styles = f'''<?xml version="1.0" encoding="UTF-8"?><styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><numFmts count="{len(customs)}">{numfmts}</numFmts><fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="{len(ids)}">{xfs}</cellXfs><dxfs count="1"><dxf><numFmt numFmtId="200" formatCode="&quot;CF: &quot;0.000"/></dxf></dxfs></styleSheet>'''
strings = []
rows = []
for r, (label, v, t, i, _) in enumerate(cases, start=1):
    strings.append(label); a = f'<c r="A{r}" t="s"><v>{len(strings)-1}</v></c>'
    s = xf_index[i]
    if t == "s":
        strings.append(v); b = f'<c r="B{r}" s="{s}" t="s"><v>{len(strings)-1}</v></c>'
    elif t == "n": b = f'<c r="B{r}" s="{s}"><v>{v}</v></c>'
    else: b = f'<c r="B{r}" s="{s}" t="{t}"><v>{v}</v></c>'
    rows.append(f'<row r="{r}">{a}{b}</row>')
# conditional format on a cell with numFmt 2 to switch its number format
n = len(cases) + 1
rows.append(f'<row r="{n}"><c r="A{n}" t="s"><v>{len(strings)}</v></c><c r="B{n}" s="{xf_index[2]}"><v>7</v></c></row>'); strings.append("conditional numFmt")
sheet = f'''<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(rows)}</sheetData><conditionalFormatting sqref="B{n}"><cfRule type="cellIs" dxfId="0" priority="1" operator="greaterThan"><formula>5</formula></cfRule></conditionalFormatting></worksheet>'''
esc = lambda s: s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
sst = '<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' + "".join(f"<si><t xml:space=\"preserve\">{esc(s)}</t></si>" for s in strings) + "</sst>"
date1904 = len(sys.argv) > 2
wb = f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">{"<workbookPr date1904=\"1\"/>" if date1904 else ""}<sheets><sheet name="Formats" sheetId="1" r:id="rId1"/></sheets></workbook>'
with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/><Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/></Types>')
    z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
    z.writestr("xl/_rels/workbook.xml.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>')
    z.writestr("xl/workbook.xml", wb); z.writestr("xl/worksheets/sheet1.xml", sheet); z.writestr("xl/styles.xml", styles); z.writestr("xl/sharedStrings.xml", sst)
