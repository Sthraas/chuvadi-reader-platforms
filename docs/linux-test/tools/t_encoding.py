# Encoding picker (D-191) spot check: a Windows-1252 text file on Automatic, read as UTF-8, and back; the file's bytes
# never change. Usage: t_encoding.py <work dir>
import helpers as h, hashlib
from lt_base import *
W = sys.argv[1]; os.makedirs(W, exist_ok=True); F = os.path.join(W, "enc-1252.txt")
RAW = b"caf\xe9 \x96 \x93quoted\x94 \x80 5 na\xefve\n"; open(F, "wb").write(RAW)
a = App(APP, EV + "/encoding", display=":97"); h.bind(a); a.start_display()
text = lambda: a.js("var t=document.querySelector('.shell').innerText; var i=t.indexOf('caf'); return i<0?'not found':t.slice(i,i+32)")
btn = lambda: a.js("var b=[...document.querySelectorAll('.statusbar button')].filter(b=>b.offsetParent).map(b=>b.innerText.trim()).filter(t=>/UTF|Windows|Automatic|ISO/i.test(t)); return b")
rows = lambda: a.js("return [...document.querySelectorAll('.enc-row')].map(r => r.querySelector('.enc-n').textContent.trim() + (r.getAttribute('aria-checked') === 'true' ? '*' : ''))")
note = lambda: a.js("var e=document.querySelector('.fc-status.err'); return e ? e.textContent.trim() : ''")
def open_card(): a.js("var b=[...document.querySelectorAll('.sb-btn')].find(b => (b.title||'').startsWith('Read this file as')); b.click(); return 1"); time.sleep(1)
def choose(lab):
    ok = a.js(f"var r=[...document.querySelectorAll('.enc-row')].find(r => r.querySelector('.enc-n').textContent.trim() === '{lab}'); if (!r) return false; r.click(); return true"); time.sleep(1.5); return ok
try:
    a.launch(); time.sleep(3); a.send("open " + F, timeout=15); time.sleep(3)
    print("ENC Automatic:", repr(text()), "| status-bar button:", btn(), flush=True)
    open_card(); print("ENC card rows:", rows(), flush=True)
    print("ENC choose UTF-8:", choose("UTF-8"), "->", repr(text()), "| button:", btn(), "| card says:", note(), flush=True)
    print("ENC choose Automatic:", choose("Automatic"), "->", repr(text()), "| button:", btn(), flush=True)
    print("ENC file bytes unchanged:", open(F, "rb").read() == RAW, flush=True)
finally: a.stop()
