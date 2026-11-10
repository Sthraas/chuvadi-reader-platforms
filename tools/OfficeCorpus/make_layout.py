# TESTING ONLY (file-fidelity audit E-05 to E-16, D-171, D-172): layout.xlsx, written straight as XML so what the
# file holds is known. Usage: python3 make_layout.py ../../tests/ChuvadiReader.Tests/Fixtures/Office/layout.xlsx
import zipfile, sys
NS = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
R = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'

def s(text): return f'<is><t xml:space="preserve">{text}</t></is>'
def cell(ref, style=0, text=None, num=None, rich=None):
    if rich is not None: return f'<c r="{ref}" s="{style}" t="inlineStr"><is>{rich}</is></c>'
    if text is not None: return f'<c r="{ref}" s="{style}" t="inlineStr">{s(text)}</c>'
    if num is not None: return f'<c r="{ref}" s="{style}"><v>{num}</v></c>'
    return f'<c r="{ref}" s="{style}"/>'
def row(n, cells, extra=''): return f'<row r="{n}"{extra}>{"".join(cells)}</row>'

styles = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet {NS}>
<fonts count="5">
 <font><sz val="11"/><name val="Calibri"/></font>
 <font><strike/><sz val="11"/><name val="Calibri"/></font>
 <font><u val="double"/><sz val="11"/><name val="Calibri"/></font>
 <font><vertAlign val="superscript"/><sz val="11"/><name val="Calibri"/></font>
 <font><b/><sz val="14"/><name val="Calibri"/></font>
</fonts>
<fills count="4">
 <fill><patternFill patternType="none"/></fill>
 <fill><patternFill patternType="gray125"/></fill>
 <fill><patternFill patternType="solid"><fgColor rgb="FFFFFF00"/></patternFill></fill>
 <fill><patternFill patternType="lightGray"><fgColor rgb="FF0000FF"/><bgColor rgb="FFFFFFFF"/></patternFill></fill>
</fills>
<borders count="3">
 <border><left/><right/><top/><bottom/><diagonal/></border>
 <border><left style="thin"><color rgb="FFFF0000"/></left><right/><top/><bottom style="thick"><color rgb="FF000000"/></bottom><diagonal/></border>
 <border><left style="thin"><color auto="1"/></left><right style="thin"><color auto="1"/></right><top style="double"><color rgb="FF008000"/></top><bottom style="dashed"><color auto="1"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="13">
 <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
 <xf numFmtId="0" fontId="4" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
 <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
 <xf numFmtId="0" fontId="0" fillId="0" borderId="2" xfId="0" applyBorder="1"/>
 <xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>
 <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
 <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
 <xf numFmtId="0" fontId="0" fillId="3" borderId="0" xfId="0" applyFill="1"/>
 <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="left" indent="2"/></xf>
 <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment textRotation="45"/></xf>
 <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1" vertical="top"/></xf>
 <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="right"/></xf>
 <xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
</cellXfs>
</styleSheet>'''

rich = ('<r><t>H</t></r><r><rPr><vertAlign val="subscript"/><sz val="11"/><rFont val="Calibri"/></rPr><t>2</t></r>'
        '<r><t xml:space="preserve">O </t></r><r><rPr><b/><sz val="11"/><color rgb="FFFF0000"/><rFont val="Calibri"/></rPr><t>bold red</t></r>')
rows = [
 row(1, [cell('A1', 1, 'Title merged'), cell('B1', 1)]),
 row(2, [cell('A2', 1), cell('B2', 1)]),
 row(3, [cell('A3', 0, 'tall row')], ' ht="30" customHeight="1"'),
 row(4, [cell('A4', 0, 'This text is long and runs over the empty cells beside it'), cell('D4', 0, 'stop'), cell('H4', 11, 'runs over to the left')]),
 row(5, [cell('A5', 0, 'in a hidden row')], ' hidden="1"'),
 row(6, [cell('A6', 2, 'borders'), cell('B6', 3), cell('C6', 0, 'in a hidden column')]),
 row(7, [cell('A7', 4, 'struck'), cell('B7', 5, 'double underline'), cell('D7', 6, 'super')]),
 row(8, [cell('A8', 0, rich=rich)]),
 row(9, [cell('A9', 0, num=10), cell('B9', 0, num=10)]),
 row(10, [cell('A10', 0, num=50), cell('B10', 0, num=50)]),
 row(11, [cell('A11', 0, num=90), cell('B11', 0, num=90)]),
 row(12, [cell('A12', 0, 'has a comment')]),
 row(13, [cell('A13', 0, 'Example site')]),
 row(14, [cell('A14', 7, 'pattern fill')]),
 row(15, [cell('A15', 8, 'indented'), cell('B15', 9, 'turned')]),
 row(16, [cell('A16', 10, 'wrapped text that takes more than one line in its cell')], ' ht="48" customHeight="1"'),
 row(17, [cell('A17', 0, num=1234567)]),
 row(18, [cell('A18', 12, num=7654321)]),
 row(6000, [cell('KN6000', 0, 'far away')]),
]
sheet1 = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet {NS} {R}>
<sheetViews><sheetView workbookViewId="0"><pane xSplit="1" ySplit="2" topLeftCell="B3" activePane="bottomRight" state="frozen"/></sheetView></sheetViews>
<sheetFormatPr defaultRowHeight="15"/>
<cols><col min="1" max="1" width="20" customWidth="1"/><col min="3" max="3" width="9" hidden="1" customWidth="1"/><col min="5" max="5" width="5" customWidth="1"/></cols>
<sheetData>{"".join(rows)}</sheetData>
<mergeCells count="1"><mergeCell ref="A1:B2"/></mergeCells>
<conditionalFormatting sqref="A9:A11"><cfRule type="dataBar" priority="1"><dataBar><cfvo type="min"/><cfvo type="max"/><color rgb="FF638EC6"/></dataBar></cfRule></conditionalFormatting>
<conditionalFormatting sqref="B9:B11"><cfRule type="iconSet" priority="2"><iconSet iconSet="3Arrows"><cfvo type="percent" val="0"/><cfvo type="percent" val="33"/><cfvo type="percent" val="67"/></iconSet></cfRule></conditionalFormatting>
<hyperlinks><hyperlink ref="A13" r:id="rId1" tooltip="Opens the example site"/></hyperlinks>
</worksheet>'''
sheet2 = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet {NS}>
<sheetViews><sheetView workbookViewId="0" rightToLeft="1" showGridLines="0" zoomScale="150"/></sheetViews>
<sheetData>{row(1, [cell('A1', 0, 'right to left'), cell('B1', 0, num=42)])}</sheetData>
</worksheet>'''
def plain(text): return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet {NS}><sheetData>{row(1, [cell("A1", 0, text)])}</sheetData></worksheet>'
comments = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<comments {NS}><authors><author>Arun</author></authors><commentList><comment ref="A12" authorId="0"><text><r><t>Check this figure</t></r></text></comment></commentList></comments>'''
files = {
 '[Content_Types].xml': '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
<Override PartName="/xl/comments1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.comments+xml"/>
''' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1, 5)) + '</Types>',
 '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
 'xl/workbook.xml': f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook {NS} {R}><sheets><sheet name="Layout" sheetId="1" r:id="rId1"/><sheet name="Settings" sheetId="2" r:id="rId2"/><sheet name="Secret" sheetId="3" state="hidden" r:id="rId3"/><sheet name="Deep" sheetId="4" state="veryHidden" r:id="rId4"/></sheets></workbook>',
 'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, 5)) + '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
 'xl/styles.xml': styles,
 'xl/worksheets/sheet1.xml': sheet1,
 'xl/worksheets/_rels/sheet1.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.org/page" TargetMode="External"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments" Target="../comments1.xml"/></Relationships>',
 'xl/comments1.xml': comments,
 'xl/worksheets/sheet2.xml': sheet2,
 'xl/worksheets/sheet3.xml': plain('in a hidden sheet'),
 'xl/worksheets/sheet4.xml': plain('in a very hidden sheet'),
}
with zipfile.ZipFile(sys.argv[1], 'w', zipfile.ZIP_DEFLATED) as z:
    for name, data in files.items():
        z.writestr(zipfile.ZipInfo(name, (2026, 11, 11, 0, 0, 0)), data)
