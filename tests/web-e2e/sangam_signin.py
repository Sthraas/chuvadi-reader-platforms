"""End-to-end sign-in against a Sangam run locally from arunshivab/sangam (read-only; test only).

Registers a throwaway person on the local Sangam (codes read from its Development outbox), then:
portal -> Sangam sign-in -> consent -> back to the portal signed in -> the Reader shows the
person's name -> sign out -> Sangam end-session -> signed-out page -> the portal asks to sign in again.
Also checks that a back-channel logout from Sangam ends an open tab (optional, see --backchannel).

Usage: python3 sangam_signin.py <portal base> <sangam base> <out folder>
"""
import re, sys, time, os, random, string
from playwright.sync_api import sync_playwright

portal, sangam, out = sys.argv[1].rstrip('/'), sys.argv[2].rstrip('/'), sys.argv[3]
results = []

def check(name, ok, detail=""):
    results.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + (" — " + str(detail) if detail else ""))

def outbox_code(page, address):
    """Newest 6-digit code sent to the address (Sangam's Development outbox)."""
    for _ in range(20):
        page.goto(sangam + "/dev/outbox")
        text = page.inner_text("body")
        idx = text.find(address)
        if idx >= 0:
            m = re.search(r"\b(\d{6})\b", text[idx:idx + 4000])
            if m:
                return m.group(1)
        time.sleep(0.5)
    return None

tag = "".join(random.choice(string.ascii_lowercase) for _ in range(8))
email = f"chuvadi.e2e.{tag}@example.in"
mobile = "9" + "".join(random.choice(string.digits) for _ in range(9))
password = "Chuvadi-e2e-" + tag + "-Pass!"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()

    # Register through the portal's own sign-in (so the return goes back to the portal).
    page.goto(portal + "/")
    page.wait_for_url(sangam + "/login**", timeout=30000)
    check("portal sends an anonymous visitor to Sangam", page.url.startswith(sangam + "/login"))
    page.click("text=Create an account")
    page.fill("input[name=FirstName]", "Chuvadi")
    page.fill("input[name=LastName]", "Tester")
    page.fill("input[name=Email]", email)
    page.fill("input[name=MobileNumber]", mobile)
    page.fill("input[name=BirthDay]", "17")
    page.select_option("select[name=BirthMonth]", index=5)
    page.fill("input[name=BirthYear]", "1990")
    page.select_option("select[name=Gender]", index=4)
    page.fill("input[name=Password]", password)
    page.check("input[name=AcceptTerms]")
    time.sleep(3)  # Sangam's anti-bot check refuses forms sent within 2 s of being shown
    page.click("button[type=submit]:has-text('Create account')")
    page.wait_for_load_state("networkidle")
    after_register = page.url
    page.screenshot(path=os.path.join(out, "sangam-1-after-register.png"))

    # Verify whatever Sangam asks for next, with codes from its Development outbox (email, then SMS).
    for step in range(6):
        if page.url.startswith(portal):
            break
        body = page.inner_text("body")
        code_input = page.query_selector("input[name=Code], input[name=code], input[autocomplete=one-time-code]")
        if code_input:
            target = mobile[-4:] if ("mobile" in body.lower() or "sms" in body.lower() or "phone" in body.lower()) and "email" not in body.lower()[:200] else email
            back = page.url
            code = outbox_code(page, email) if target == email else outbox_code(page, mobile[-4:])
            page.goto(back)
            page.fill("input[name=Code], input[name=code], input[autocomplete=one-time-code]", code or "000000")
            time.sleep(3)
            page.click("button[type=submit]")
            page.wait_for_load_state("networkidle")
            continue
        # Consent or "continue" screens.
        for label in ["Allow", "Continue", "Agree", "Yes", "Skip", "Not now", "Later"]:
            btn = page.query_selector(f"button:has-text('{label}'), a:has-text('{label}')")
            if btn:
                time.sleep(3)
                btn.click()
                page.wait_for_load_state("networkidle")
                break
        else:
            break

    page.screenshot(path=os.path.join(out, "sangam-2-final.png"))
    print("after register:", after_register)
    print("now at:", page.url)
    check("Sangam returns to the portal after sign-in", page.url.startswith(portal), page.url[:120])

    if page.url.startswith(portal):
        page.wait_for_selector("nav.leftbar", timeout=30000)
        time.sleep(2)
        status = page.inner_text("body")
        check("the Reader shows the person's Sangam name", "Chuvadi" in status, "")
        cookies = {c["name"]: c for c in ctx.cookies(portal)}
        sess = cookies.get("chvd.session") or cookies.get("__Host-chvd")
        check("portal session cookie is HttpOnly, SameSite=Lax", bool(sess) and sess["httpOnly"] and sess["sameSite"] == "Lax")
        check("no sign-in flow cookie left behind", not any(n.startswith("chvd.oidc.") for n in cookies))
        page.screenshot(path=os.path.join(out, "sangam-3-portal.png"))

        # A second tab of the same sign-in, to check sign-out ends it too.
        tab2 = ctx.new_page()
        tab2.goto(portal + "/library")
        tab2.wait_for_selector("nav.leftbar", timeout=30000)

        # Sign out: portal -> Sangam end-session -> signed-out page.
        page.goto(portal + "/signout")
        page.wait_for_load_state("networkidle")
        for label in ["Sign out", "Yes", "Continue"]:
            btn = page.query_selector(f"button:has-text('{label}')")
            if btn and not page.url.startswith(portal):
                btn.click()
                page.wait_for_load_state("networkidle")
                break
        check("sign-out ends on the portal's signed-out page", page.url.startswith(portal + "/signed-out"), page.url[:120])
        for _ in range(40):
            if tab2.url.startswith(portal + "/signed-out"):
                break
            tab2.wait_for_timeout(250)  # not time.sleep: the sync API only sees navigations while it runs
        check("the other open tab of that sign-in is ended too", tab2.url.startswith(portal + "/signed-out"), tab2.url[:120])
        page.goto(portal + "/")
        page.wait_for_load_state("networkidle")
        check("after sign-out the portal asks to sign in again", page.url.startswith(sangam + "/login"), page.url[:120])

        # Sign in again, then sign out on Sangam itself (not through the portal): Sangam's back-channel
        # logout must end the open portal tab. Needs the portal's back-channel address registered in Sangam.
        page.fill("input[name=Identifier]", email)
        time.sleep(3)
        page.click("button[type=submit]:has-text('Continue')")
        page.wait_for_load_state("networkidle")
        if "/login/method" in page.url:
            page.click("text=Password")
            page.wait_for_load_state("networkidle")
        pw = page.query_selector("input[type=password]")
        if pw:
            pw.fill(password)
            time.sleep(3)
            page.click("button[type=submit]")
            page.wait_for_load_state("networkidle")
        for label in ["Allow", "Continue", "Not now", "Skip", "Later"]:
            if page.url.startswith(portal):
                break
            btn = page.query_selector(f"button:has-text('{label}')")
            if btn:
                time.sleep(3)
                btn.click()
                page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(out, "sangam-4-second-signin.png"))
        print("second sign-in at:", page.url[:100], "|", page.inner_text("body")[:300].replace("\n", " "))
        page.wait_for_selector("nav.leftbar", timeout=30000)
        check("signed in again with the password", page.url.startswith(portal))
        other = ctx.new_page()
        other.goto(sangam + "/connect/endsession")
        other.wait_for_load_state("networkidle")
        btn = other.query_selector("button[type=submit]")
        if btn:
            time.sleep(3)
            btn.click()
            other.wait_for_load_state("networkidle")
        # Sangam sends back-channel logouts from a background job, so allow up to a minute.
        t0 = time.time()
        for _ in range(240):
            if page.url.startswith(portal + "/signed-out"):
                break
            page.wait_for_timeout(250)
        print("back-channel took %.1f s" % (time.time() - t0))
        check("signing out on Sangam ends the portal tab (back-channel)", page.url.startswith(portal + "/signed-out"), page.url[:120])

    b.close()

print("e2e person:", email)
sys.exit(0 if all(ok for _, ok in results) else 1)
