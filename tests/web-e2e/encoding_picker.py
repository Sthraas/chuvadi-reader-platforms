"""D-191 on the portal: the encoding chosen for a text file stays inside the person's session.

A UTF-8 text file with accented words is opened; the status bar names the encoding it was read as. The
person chooses "Windows-1252" in "Read this file as": the text is read again (the accents turn into two
letters each, which is what that choice means) and the status bar says Windows-1252. After a page reload the
tab comes back still read that way (the choice is with the session's Recents entry). A second person who
opens a file of the same name and content gets Automatic and the proper accents: nothing of the first
person's choice reaches them. The first person, signed out and in again, also starts from Automatic.
Development sign-in.

Usage: python3 encoding_picker.py <portal base> <out dir> [--browser chrome|chromium|firefox|webkit]
"""
import os
import sys

from playwright.sync_api import sync_playwright

from pdfs import sign_in_as, sign_out

base, out = sys.argv[1].rstrip("/"), sys.argv[2]
engine = sys.argv[sys.argv.index("--browser") + 1] if "--browser" in sys.argv else "chrome"
results = []
os.makedirs(out, exist_ok=True)
txt = os.path.join(out, "accents.txt")
with open(txt, "wb") as f:
    f.write("Un café déjà vu, naïve et sincère.\nSecond line, plain.\n".encode("utf-8"))

AS_UTF8, AS_1252 = "café déjà vu", "cafÃ© dÃ©jÃ  vu"
BUTTON = "button.sb-btn[title]:has(svg)"
TEXT = "() => (document.querySelector('.txv') || document.body).innerText.replace(/\\u00a0/g, ' ')"


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS" if ok else "FAIL") + ": " + name + (" — " + str(detail).replace("\n", " ") if detail != "" else ""))


def open_text(page):
    page.goto(base + "/")
    page.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with page.expect_file_chooser(timeout=15000) as fc:
        page.click("nav.leftbar >> text=Upload")
    fc.value.set_files(txt)
    page.wait_for_url("**/reader**", timeout=30000)
    page.wait_for_function("() => document.querySelector('.txv') && document.querySelector('.txv').innerText.includes('Second line')", timeout=30000)
    page.wait_for_timeout(800)


def shows(page, want, timeout=15000):
    try:
        page.wait_for_function("want => (" + TEXT + ")().includes(want)", arg=want, timeout=timeout)
        return True
    except Exception:  # noqa: BLE001
        return False


def enc_button(page):
    return page.locator("button.sb-btn[aria-label*='Now ']").first


def chosen_row(page):
    enc_button(page).click()
    page.wait_for_selector(".enc-list", timeout=10000)
    on = page.locator(".enc-row.on .enc-n").all_inner_texts()
    return on[0] if len(on) == 1 else on


with sync_playwright() as p:
    if engine == "chrome":
        b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    else:
        b = getattr(p, "chromium" if engine == "chromium" else engine).launch()

    # --- the first person chooses an encoding -------------------------------------------------------------
    one = b.new_context(viewport={"width": 1400, "height": 900})
    who = sign_in_as(one, base, "enc-one-" + engine)
    page = one.new_page()
    errors = []
    # Firefox reports its circuit's socket closing as a page leaves (Sign out going to /signout); that is the
    # browser leaving, not a portal error (as in flows.py and close_card.py).
    leaving = ("was interrupted while the page was loading", "WebSocket closed with status code: 1006",
               "WebSocket is not in the OPEN state", "Cannot send data if the connection is not in the 'Connected' State")

    def page_error(e):
        if not (engine == "firefox" and any(x in str(e) for x in leaving)):
            errors.append(str(e))

    page.on("pageerror", page_error)
    open_text(page)
    check("the file opens read automatically, accents right", shows(page, AS_UTF8), page.evaluate(TEXT)[:60])
    label = enc_button(page).inner_text().strip()
    check("the status bar names the encoding", label == "UTF-8", label)
    check("Automatic is the choice to begin with", chosen_row(page) == "Automatic")
    page.click(".enc-row:has(.enc-n:text-is('Windows-1252'))")
    check("choosing Windows-1252 reads the same bytes again that way", shows(page, AS_1252), page.evaluate(TEXT)[:60])
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    label = enc_button(page).inner_text().strip()
    check("... and the status bar says so", label == "Windows-1252", label)

    page.reload()
    page.wait_for_selector("nav.leftbar", timeout=30000)
    check("after a reload the tab is still read as chosen", shows(page, AS_1252, timeout=30000), page.evaluate(TEXT)[:60])
    check("... with the choice still marked in the card", chosen_row(page) == "Windows-1252")
    page.keyboard.press("Escape")

    # --- a second person, same file name and content ------------------------------------------------------
    two = b.new_context(viewport={"width": 1400, "height": 900})
    sign_in_as(two, base, "enc-two-" + engine)
    other = two.new_page()
    other.on("pageerror", page_error)
    open_text(other)
    check("a second person's file of the same name is read automatically", shows(other, AS_UTF8) and AS_1252 not in other.evaluate(TEXT), other.evaluate(TEXT)[:60])
    check("... Automatic is their choice: nothing of the first person's reached them", chosen_row(other) == "Automatic")
    other.keyboard.press("Escape")
    check("the first person still has their choice", shows(page, AS_1252) and enc_button(page).inner_text().strip() == "Windows-1252")
    sign_out(two, base)

    # --- the first person signs out and in again: a new session starts from Automatic ---------------------
    sign_out(one, base)
    again = b.new_context(viewport={"width": 1400, "height": 900})
    again.add_cookies([{"name": "chvd-dev-user", "value": who, "url": base}])  # the very same person
    back = again.new_page()
    back.on("pageerror", page_error)
    open_text(back)
    check("signed out and in again, the same person starts from Automatic", shows(back, AS_UTF8) and chosen_row(back) == "Automatic")
    back.keyboard.press("Escape")

    # --- WT-26 / D-197: UTF-16 text comes in when it carries its byte-order mark ---------------------------
    words = "Un café en UTF-16, déjà vu.\nSecond line, plain.\n"
    for name, data, label in [("utf16le.txt", b"\xff\xfe" + words.encode("utf-16-le"), "UTF-16 LE"),
                              ("utf16be.txt", b"\xfe\xff" + words.encode("utf-16-be"), "UTF-16 BE")]:
        path = os.path.join(out, name)
        open(path, "wb").write(data)
        back.goto(base + "/")
        back.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
        with back.expect_file_chooser(timeout=15000) as fc:
            back.click("nav.leftbar >> text=Upload")
        fc.value.set_files(path)
        ok = shows(back, "café en UTF-16, déjà vu", timeout=30000)
        said = enc_button(back).inner_text().strip() if ok else ""
        check("a %s text file with its byte-order mark opens, read right" % label, ok and said == label, said or back.evaluate(TEXT)[:60])

    nomark = os.path.join(out, "utf16-nomark.txt")
    open(nomark, "wb").write(words.encode("utf-16-le"))
    back.goto(base + "/")
    back.wait_for_selector("nav.leftbar >> text=Upload", timeout=30000)
    with back.expect_file_chooser(timeout=15000) as fc:
        back.click("nav.leftbar >> text=Upload")
    fc.value.set_files(nomark)
    try:
        back.wait_for_selector("text=UTF-16 text saved without a byte-order mark", timeout=15000)
        message = back.locator("text=UTF-16 text saved without a byte-order mark").first.inner_text()
        check("UTF-16 without the mark is refused, and the message says what to do", "Save it as UTF-8, or as UTF-16 with a byte-order mark" in message and "isn't a valid" not in message, message[:160])
    except Exception as ex:  # noqa: BLE001
        check("UTF-16 without the mark is refused, and the message says what to do", False, str(ex)[:120])
    check("no page errors", not errors, "; ".join(errors[:3]))
    sign_out(again, base)
    b.close()

sys.exit(0 if all(results) else 1)
