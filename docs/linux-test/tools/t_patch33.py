# Patch 33 on Linux (D-198, D-200), Linux Test's own check with real mouse and keyboard in the real window:
#   redaction   Protect shows one greyed "Redaction" saying it comes back; R and /redact give no way in
#   signature   a signed PDF shows what the signature states and no verdict ("not checked in this version")
#   pageops     every page operation asks first and names what each file loses: Arrange's Bind, Merge, Split;
#               then the saved results are read back to see that the warning was true; originals untouched
#   bind        the same for Arrange's Bind, in its own run (each file is asked about once per run)
#   excel       conditional colours are not drawn, the values and the cells' own formats are, and the sheet says so
# Fixtures (made by Linux Test): plain.pdf, rich.pdf (bookmarks, page labels, language), layered.pdf (a hidden
# layer), signed.pdf (pyHanko, a self-made test certificate), cond.xlsx (cell rule, colour scale, data bar).
# Usage: t_patch33.py <fixture dir> <work dir> <part>
import helpers as h, json, hashlib, shutil
from lt_base import *
FX, WORK, PART = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(WORK, exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
def P(*x): print(*x, flush=True)
def fresh(name, as_=None):
    p = os.path.join(WORK, as_ or name); shutil.copyfile(os.path.join(FX, name), p); return p
a = App(APP, EV + f"/patch33-{PART}", display=f":{ {'redaction': 51, 'signature': 52, 'pageops': 53, 'excel': 54, 'bind': 55}[PART] }"); h.bind(a); a.start_display()
def wait_pages(t=30): a.wait(lambda: a.js("return document.querySelectorAll('.rdesk .rpage svg').length > 0"), t, "pages")
def open_tab(path, pdf=True):
    n = os.path.basename(path); a.send("open " + path, timeout=15)
    a.wait(lambda: a.js(f"var t=document.querySelector('.rtab.active'); return !!t && t.innerText.includes('{n}')"), 30, n)
    if pdf: wait_pages()
    time.sleep(1.5)
def key(k): h.focus_main(); a.xdo("key", k); time.sleep(0.8)
def desk_click():
    r = a.js("var e=document.querySelector('.rdesk') || document.querySelector('main'); var r=e.getBoundingClientRect(); return [r.left, r.top]")
    a.xdo("mousemove", str(int(r[0] + 20)), str(int(r[1] + 20))); a.xdo("click", "1"); time.sleep(0.3)
def toast(): return a.js("return [...document.querySelectorAll('.msgs .msg, .toast, .snack, .notify, [role=status]')].map(e => e.innerText.trim()).filter(t => t).slice(-3)")
opcard = lambda: a.js("var c=document.querySelector('.pageopq'); return c ? {title: c.querySelector('.closeq-title').textContent.trim(), text: c.querySelector('.closeq-text').textContent.replace(/\\s+/g,' ').trim(), buttons: [...c.querySelectorAll('button')].map(b => b.textContent.trim()), focus: document.activeElement ? document.activeElement.textContent.trim() : null} : null")
def op_answer(label):
    a.js(f"var b=[...document.querySelectorAll('.pageopq button')].find(b => b.textContent.trim().startsWith('{label}')); b.click(); return 1"); time.sleep(1.2)
def catalog(path):
    code = ("import pikepdf,sys\np=pikepdf.open(sys.argv[1]); r=p.Root\n"
            "with p.open_outline() as o: bm=[i.title for i in o.root]\n"
            "print({'pages': len(p.pages), 'bookmarks': bm, 'page_labels': '/PageLabels' in r, 'lang': str(r.get('/Lang')) if '/Lang' in r else None, 'layers': '/OCProperties' in r})")
    o = subprocess.run(["python3", "-c", code, path], capture_output=True, text=True); return (o.stdout or o.stderr).strip()[:300]
def text_of(path): return subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True).stdout.replace("\x0c", " | ").replace("\n", " ").strip()[:200]
try:
    a.launch()
    if PART == "redaction":
        f = fresh("plain.pdf", "rd-plain.pdf"); open_tab(f); desk_click(); key("4"); time.sleep(0.5)
        rail = a.js("return [...document.querySelectorAll('button')].filter(b => b.offsetParent && /redact/i.test((b.getAttribute('aria-label')||'') + ' ' + b.textContent)).map(b => ({label: (b.getAttribute('aria-label') || b.textContent).trim().slice(0,60), disabled: b.disabled || b.getAttribute('aria-disabled') === 'true', title: (b.title || b.getAttribute('data-reason') || '').slice(0,120)}))")
        P("PROTECT rail, buttons about redaction:", json.dumps(rail))
        others = a.js("return [...document.querySelectorAll('.srail button')].filter(b => b.offsetParent).map(b => (b.getAttribute('aria-label')||b.textContent).trim().split(/\\s{2,}|\\n/)[0]).slice(0,20)")
        P("  the rest of Protect's rail:", others)
        btn = a.js("var b=[...document.querySelectorAll('.srail button')].find(b => b.offsetParent && /Redaction/.test((b.getAttribute('aria-label')||'') + b.textContent)); if(!b) return null; var r=b.getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]")
        if btn:
            a.xdo("mousemove", str(int(btn[0])), str(int(btn[1]))); time.sleep(1.2); a.xdo("click", "1"); time.sleep(1)
            P("  tap on the greyed Redaction -> reason shown:", a.js("return [...document.querySelectorAll('.msgs .msg, .tip, .tooltip, .rb-reason, .reason, [role=tooltip], .toast')].map(e => e.innerText.trim()).filter(t => t).slice(-3)"), "| page:", a.js("return location.pathname"))
        sv = a.js("var b=[...document.querySelectorAll('.srail button')].find(b => b.offsetParent && /Save redacted copy/.test((b.getAttribute('aria-label')||'') + b.textContent)); if(!b) return null; var r=b.getBoundingClientRect(); return [r.left + r.width/2, r.top + r.height/2]")
        if sv:   # B-36: greyed with its reason from patch 34
            a.xdo("mousemove", str(int(sv[0])), str(int(sv[1]))); time.sleep(1.2); a.xdo("click", "1"); time.sleep(1)
            P("  click on Save redacted copy -> notice:", a.js("return [...document.querySelectorAll('.msgs .msg, .toast, [role=status], .notice')].map(e => e.innerText.trim()).filter(t => t).slice(-2)"), "| page:", a.js("return location.pathname"), "| save dialog:", bool(subprocess.run(["xdotool", "search", "--onlyvisible", "--name", "Save"], env=a.env, capture_output=True, text=True).stdout.split()))
        desk_click(); key("r"); time.sleep(0.8); P("R key in Protect -> page:", a.js("return location.pathname"), "| drawing layer:", a.js("return !!document.querySelector('.mk-layer.drawmode')"), "| notice:", toast())
        cmds = a.send("commands"); held = [c for c in (cmds if isinstance(cmds, list) else json.loads(cmds) if isinstance(cmds, str) and cmds.startswith('[') else []) if isinstance(c, dict) and c.get("id") in ("p.redact", "p.find")]
        P("COMMANDS p.redact, p.find:", json.dumps(held)[:400] if held else str(cmds)[:300])
        a.js("Blazor.navigateTo('/redact'); return 1"); time.sleep(1.5)
        P("/redact directly -> says:", a.js("var e=document.querySelector('.rd-held'); return e ? e.innerText.replace(/\\s+/g,' ').trim() : null"), "| anything to draw or search:", a.js("return document.querySelectorAll('.mk-layer, .rd-find').length"))
        P("  file untouched:", sha(f) == sha(os.path.join(FX, "plain.pdf")))
    if PART == "signature":
        f = fresh("signed.pdf", "sig-signed.pdf"); open_tab(f); time.sleep(2)
        P("SIGNED file, banner:", a.js("var b=document.querySelector('.sig-banner'); return b ? [b.className, b.innerText.replace(/\\s+/g,' ').trim()] : null"))
        a.js("var b=document.querySelector('.sig-banner .details'); if (b) b.click(); return 1"); time.sleep(2.5)
        card = a.js("var c=[...document.querySelectorAll('.sig')]; return c.map(e => e.innerText.replace(/\\s+/g,' ').trim().slice(0,600))")
        P("  Details card:", json.dumps(card, ensure_ascii=False))
        body = a.js("return document.body.innerText")
        P("  verdict words anywhere on screen:", [w for w in ("Valid", "valid signature", "Not valid", "Trusted", "trusted", "changed after", "tampered") if w in body])
        P("  file untouched:", sha(f) == sha(os.path.join(FX, "signed.pdf")))
        u = fresh("plain.pdf", "sig-unsigned.pdf"); open_tab(u); time.sleep(1.5)
        P("UNSIGNED file, banner:", a.js("var b=document.querySelector('.sig-banner'); return b ? b.innerText.trim() : null"))
    if PART == "pageops":
        fp, fr, fl = fresh("plain.pdf", "op-plain.pdf"), fresh("rich.pdf", "op-rich.pdf"), fresh("layered.pdf", "op-layered.pdf")
        orig = {p: sha(p) for p in (fp, fr, fl)}
        P("SOURCES:", "rich", catalog(fr), "| layered", catalog(fl), "| layered text:", text_of(fl))
        open_tab(fp); open_tab(fr)
        # Merge (the open tabs)
        a.send("invoke doc.merge"); time.sleep(2)
        a.js("[...document.querySelectorAll('button.tbtn')].find(b => b.textContent.includes('Add open documents')).click(); return 1"); time.sleep(1)
        P("MERGE entries:", a.js("return (document.body.innerText.match(/op-[a-z]+\\.pdf/g) || []).filter((v, i, x) => x.indexOf(v) === i)"), "| Merge button enabled:", a.js("return !document.querySelector('.tbtn-go').disabled"))
        a.js("document.querySelector('.tbtn-go').click(); return 1"); time.sleep(2)
        c = opcard(); P("  Merge asks:", json.dumps(c, ensure_ascii=False))
        a.xdo("key", "Tab"); time.sleep(0.2); P("  Tab stays inside the card:", a.js("return !!(document.activeElement && document.activeElement.closest('.pageopq'))"))
        a.xdo("key", "Escape"); time.sleep(1); P("  Esc -> card gone:", opcard() is None, "| a save dialog opened:", bool(h.native_windows()) if hasattr(h, "native_windows") else "?")
        a.js("document.querySelector('.tbtn-go').click(); return 1"); time.sleep(2); op_answer("Continue")
        out = os.path.join(WORK, "op-merged.pdf"); [os.remove(out) for _ in [0] if os.path.exists(out)]
        try: h.file_dialog("Save", out); time.sleep(3)
        except Exception as e: P("  save dialog problem:", str(e)[:120])
        P("  Continue -> merged:", catalog(out) if os.path.exists(out) else "not written")
        a.js("document.querySelector('.tbtn-go').click(); return 1"); time.sleep(2); c2 = opcard()
        P("  a second Merge of the same files asks again:", c2 is not None)
        if c2: op_answer("Cancel")
        else:
            try: h.file_dialog("Save", os.path.join(WORK, "op-merged-2.pdf")); time.sleep(2)
            except Exception: a.xdo("key", "Escape")
        # Split (Extract range) on the layered file
        a.js("Blazor.navigateTo('/reader'); return 1"); time.sleep(1); open_tab(fl); a.send("invoke doc.split"); time.sleep(2)
        if not a.js("return document.querySelectorAll('input[name=splitmode]').length + document.querySelectorAll('.tool-actions').length"):
            P("  (doc.split left the page at", a.js("return location.pathname"), "; going to /split)"); a.js("Blazor.navigateTo('/split'); return 1"); time.sleep(2.5)
        a.js("var b=[...document.querySelectorAll('button.tbtn')].find(b => b.textContent.includes('Use current')); if (b) b.click(); return 1"); time.sleep(1.5)
        P("  Split source:", a.js("var e=document.querySelector('.ssource-name'); return e ? e.textContent.trim() : null"))
        a.js("var r=[...document.querySelectorAll('input[name=splitmode]')][1]; r.click(); return 1"); time.sleep(0.8)
        a.js("document.querySelector('.tbtn-go').click(); return 1"); time.sleep(2)
        c = opcard(); P("SPLIT (extract page 1) of the layered file asks:", json.dumps(c, ensure_ascii=False))
        op_answer("Continue"); out2 = os.path.join(WORK, "op-extract.pdf"); [os.remove(out2) for _ in [0] if os.path.exists(out2)]
        try: h.file_dialog("Save", out2); time.sleep(3)
        except Exception as e: P("  save dialog problem:", str(e)[:120])
        P("  Continue -> extracted:", catalog(out2) if os.path.exists(out2) else "not written", "| text:", text_of(out2) if os.path.exists(out2) else None)
        P("ORIGINALS untouched:", all(sha(p) == orig[p] for p in orig))
    if PART == "bind":
        fp, fr = fresh("plain.pdf", "op-plain.pdf"), fresh("rich.pdf", "op-rich.pdf"); orig = {p: sha(p) for p in (fp, fr)}
        # Arrange: interleave the two first files, Bind
        open_tab(fp); open_tab(fr); desk_click(); key("3"); time.sleep(1.5)
        if not a.js("return document.querySelectorAll('.shelf-tool').length"):
            P("  (key 3 left the page at", a.js("return location.pathname"), "with tabs", a.js("return [...document.querySelectorAll('.rtab .rtab-name')].map(e => e.textContent.trim())"), "; clicking Arrange on the left bar)")
            r = a.js("var b=[...document.querySelectorAll('button')].find(b => b.offsetParent && /^Arrange/.test((b.getAttribute('aria-label')||b.textContent).trim())); if(!b) return null; var q=b.getBoundingClientRect(); return [q.left+q.width/2, q.top+q.height/2]")
            if r: a.xdo("mousemove", str(int(r[0])), str(int(r[1]))); a.xdo("click", "1")
        a.wait(lambda: a.js("return document.querySelectorAll('.shelf-tool').length > 0"), 20, "Arrange shelf"); time.sleep(1.5)
        a.js("[...document.querySelectorAll('.shelf-tool')].find(b => (b.title||'').startsWith('Weave')).click(); return 1"); time.sleep(0.8)
        names = a.js("var s=document.querySelectorAll('.shelf-interleave select'); return [...s[0].options].map(o => o.textContent.trim())")
        ia, ib = names.index(next(n for n in names if "op-plain" in n)), names.index(next(n for n in names if "op-rich" in n))
        a.js(f"var s=document.querySelectorAll('.shelf-interleave select'); s[0].selectedIndex={ia}; s[0].dispatchEvent(new Event('change')); s[1].selectedIndex={ib}; s[1].dispatchEvent(new Event('change')); return 1"); time.sleep(0.6)
        a.js("document.querySelector('.shelf-interleave .bt-prime').click(); return 1"); time.sleep(2.5)
        a.js("var b=[...document.querySelectorAll('.bt-bind')]; b[b.length-1].click(); return 1"); time.sleep(2)
        c = opcard(); P("ARRANGE Bind of a desk with pages from op-plain and op-rich asks:", json.dumps(c, ensure_ascii=False))
        op_answer("Continue"); out3 = os.path.join(WORK, "op-bound.pdf"); [os.remove(out3) for _ in [0] if os.path.exists(out3)]
        try: h.file_dialog("Save", out3); time.sleep(3)
        except Exception as e: P("  save dialog problem:", str(e)[:120])
        P("  Continue -> bound:", catalog(out3) if os.path.exists(out3) else "not written")
        a.js("var b=[...document.querySelectorAll('.bt-bind')]; b[b.length-1].click(); return 1"); time.sleep(2)
        P("  a second Bind in the same run asks again:", opcard() is not None, "(asked once per file per run, by design)")
        a.xdo("key", "Escape"); time.sleep(1)
        P("ORIGINALS untouched:", all(sha(p) == orig[p] for p in orig))
    if PART == "excel":
        f = fresh("cond.xlsx", "cf-rules.xlsx"); open_tab(f, pdf=False); time.sleep(3)
        cell = lambda addr: a.js(f"var c=document.querySelector('.xv-cell[data-a=\"{addr}\"]'); if(!c) return null; var s=getComputedStyle(c); var inner=[...c.querySelectorAll('*')].map(e => getComputedStyle(e)).map(t => t.backgroundColor + '/' + t.fontWeight).filter(x => !x.startsWith('rgba(0, 0, 0, 0)/400')); return [c.innerText.trim(), s.backgroundColor, inner, c.children.length > 1 ? [...c.children].map(e => e.className).join(',') : '']")
        P("SHEET with rules: note:", a.js("var e=document.querySelector('.xv-condheld'); return e ? [e.textContent.trim(), e.title] : null"))
        for addr in ("A2", "A3", "A4", "B2", "B6", "C3", "C4"): P(f"  {addr}:", cell(addr))
        P("  C4 markup:", a.js("var c=document.querySelector('.xv-cell[data-a=\"C4\"]'); return c ? c.outerHTML.slice(0,400) : null"), "| bold inside:", a.js("var c=document.querySelector('.xv-cell[data-a=\"C4\"]'); return c ? [...c.querySelectorAll('*')].map(e => getComputedStyle(e).fontWeight) : null"))
        a.js("[...document.querySelectorAll('.xv-tab')].find(t => t.textContent.includes('Plain')).click(); return 1"); time.sleep(1.5)
        P("SHEET without rules: note:", a.js("var e=document.querySelector('.xv-condheld'); return e ? e.textContent.trim() : null"), "| A2:", cell("A2"))
        P("  file untouched:", sha(f) == sha(os.path.join(FX, "cond.xlsx")))
    log = open(a.log_path, errors="replace").read()
    P("LOG: 'Chuvadi error' lines:", log.count("Chuvadi error"), "| GLib criticals:", log.count("CRITICAL"))
finally:
    try: a.stop()
    except Exception: pass
