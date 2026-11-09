"""Word/Excel data-fidelity corpus (Web Test chat; test tooling only).
python3 make_fidelity.py <out>  -> fid.docx, fid.xlsx (python-docx/openpyxl) + expected.json"""
import json, os, sys, datetime
import docx, openpyxl
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
TOK = ["Two  spaces here", "  leading spaces", "trailing spaces  ", "mIxEd CaSe TeXt", "Recieve teh mispelt wrod",
       "சுவடி தமிழ் உரை", "नमस्ते दुनिया", "Symbols <>&\"' end", "00123", "12345678901234567890", "UPPER lower Title",
       "a.b,c;d:e", "Ünïcödé àccents", "tab\there"]
d = docx.Document(); d.add_heading("Fidelity", 1)
for t in TOK: d.add_paragraph(t)
d.save(os.path.join(out, "fid.docx"))
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Data"
for i, t in enumerate(TOK, 1): ws.cell(i, 1, t)
num = [  # (value, number_format, expected display)
    (3.14159265358979, "General", "3.14159265358979"), (0.125, "0.00%", "12.50%"), (1234.5, "#,##0.00", "1,234.50"),
    (-42, "0", "-42"), (1234.5, '"₹"#,##0.00', "₹1,234.50"), (datetime.date(2026, 11, 9), "dd-mm-yyyy", "09-11-2026"),
    (7, "000", "007"), (1e-7, "0.00E+00", "1.00E-07"), (1, "General", "1")]
for i, (v, f, _) in enumerate(num, 1):
    c = ws.cell(i, 2, v); c.number_format = f
ws.cell(10, 3, "=B9*2")  # formula; openpyxl writes no cached value
wb.save(os.path.join(out, "fid.xlsx"))
json.dump({"tokens": TOK, "numbers": [x[2] for x in num]}, open(os.path.join(out, "expected.json"), "w"), ensure_ascii=False, indent=1)
print("ok")
