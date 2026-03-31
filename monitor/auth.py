"""
Interactive login for the ERAN portal.

Because the login page uses reCAPTCHA + SMS/email OTP, we open a real
(visible) browser window and let the user complete the login flow manually.
Once the user is logged in the session is saved to SESSION_FILE so future
runs can reuse it without logging in again.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

from monitor.config import LOGIN_URL, PORTAL_URL, SESSION_FILE, EMAIL, PASSWORD


def login_interactive() -> None:
    """
    Open a headed browser, pre-fill credentials, wait for the user to:
      1. Tick "כניסה ללא שלוחה" (login without extension)
      2. Complete reCAPTCHA
      3. Enter the OTP that arrives by email/SMS
    Then save the session to SESSION_FILE.
    """
    print("=" * 60)
    print("פותח דפדפן לכניסה ידנית לאתר ער\"ן...")
    print("  1. סמן 'כניסה ללא שלוחה'")
    print("  2. סמן 'אני לא רובוט' (reCAPTCHA)")
    print("  3. לחץ התחבר – תקבל קוד בSMS/מייל")
    print("  4. הזן את הקוד בדפדפן")
    print("  5. לאחר שהגעת לדף מרכז השיחות, חזור לכאן ולחץ Enter")
    print("=" * 60)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()
        page = context.new_page()

        page.goto(LOGIN_URL, wait_until="networkidle")

        # Pre-fill email & password if provided in config
        if EMAIL:
            try:
                page.fill('input[type="email"], input[name*="mail"], input[name*="Email"]', EMAIL)
            except Exception:
                pass
        if PASSWORD:
            try:
                page.fill('input[type="password"], input[name*="assword"]', PASSWORD)
            except Exception:
                pass

        print("\nהשלם את הכניסה בדפדפן, ואז לחץ Enter כאן...")
        input()

        # Verify we landed on the call-centre page
        current = page.url
        if "CallCenter" not in current and "default" not in current:
            print(f"[אזהרה] כתובת הדף הנוכחית: {current}")
            print("ייתכן שהכניסה לא הושלמה. ממשיך לשמור קוקיז בכל מקרה.")

        # Save storage state (cookies + localStorage)
        context.storage_state(path=SESSION_FILE)
        print(f"[✓] הסשן נשמר ב: {SESSION_FILE}")

        browser.close()


def load_session_context(pw):
    """Return a browser context with the saved session, or None if not found."""
    if not Path(SESSION_FILE).exists():
        return None
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(storage_state=SESSION_FILE)
    return browser, context


def is_session_valid(page) -> bool:
    """Check whether the current page is really the call-centre (not a login redirect)."""
    return "CallCenter" in page.url or "default.aspx" in page.url
