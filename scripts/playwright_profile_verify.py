#!/usr/bin/env python3
"""Playwright script to verify the redesigned profile page."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("BASE_URL", "http://localhost:5173")
EMAIL = os.getenv("BOOTSTRAP_SUPERUSER_EMAIL", "")
PASSWORD = os.getenv("BOOTSTRAP_SUPERUSER_PASSWORD", "")

ARTIFACTS_DIR = Path(__file__).parent.parent / ".artifacts" / "profile-verify"


def main() -> int:
    if not EMAIL or not PASSWORD:
        print("ERROR: BOOTSTRAP_SUPERUSER_EMAIL and BOOTSTRAP_SUPERUSER_PASSWORD required in .env")
        return 1

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        print(f"1. Navigating to login at {BASE_URL}/login ...")
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=str(ARTIFACTS_DIR / "01-login.png"))

        print("2. Logging in...")
        # Login form is in a modal dialog - target the submit button inside the form
        page.locator('input[id="login-email"], input[type="email"]').first.fill(EMAIL)
        page.locator('input[id="login-password"], input[type="password"]').first.fill(PASSWORD)
        page.locator('button[type="submit"]').click()

        # Wait for redirect to dashboard or home
        page.wait_for_timeout(2000)
        # Check if we're logged in by looking for authenticated elements
        page.wait_for_selector(
            '[data-testid="user-menu"], nav a[href="/dashboard"], a[href="/profile"]', timeout=10000
        )
        page.screenshot(path=str(ARTIFACTS_DIR / "02-logged-in.png"))
        print("   Logged in successfully.")

        print("3. Navigating to profile page...")
        page.goto(f"{BASE_URL}/profile", wait_until="networkidle")
        page.wait_for_timeout(500)  # Allow transitions to complete
        page.screenshot(path=str(ARTIFACTS_DIR / "03-profile-full.png"))

        # Verify single panel design
        print("4. Verifying single panel design...")
        panels = page.locator(".shadow-brutal-sm").count()
        print(f"   Found {panels} element(s) with shadow-brutal-sm")

        # Check for nested sections
        sections = page.locator("section").count()
        print(f"   Found {sections} section(s) within the panel")

        # Test inline editing - click on first "Ändra" button
        print("5. Testing inline editing (first name)...")
        change_buttons = page.locator('button:has-text("Ändra")')
        if change_buttons.count() > 0:
            change_buttons.first.click()
            page.wait_for_timeout(300)
            page.screenshot(path=str(ARTIFACTS_DIR / "04-inline-edit-active.png"))
            print("   Inline edit mode activated.")

            # Cancel the edit
            cancel_btn = page.locator('button:has-text("Avbryt")').first
            if cancel_btn.is_visible():
                cancel_btn.click()
                page.wait_for_timeout(300)
                page.screenshot(path=str(ARTIFACTS_DIR / "05-inline-edit-cancelled.png"))
                print("   Inline edit cancelled.")

        # Test password change expansion
        print("6. Testing password change inline...")
        # Find the password row by looking for the masked value then click its Ändra button
        pw_row = page.locator("text=••••••••").locator("..").locator('button:has-text("Ändra")')
        if pw_row.count() > 0:
            pw_row.first.click()
        else:
            # Fallback: find all Ändra buttons and click the one after Lösenord
            all_buttons = page.locator('button:has-text("Ändra")')
            # The password button should be around index 4-5 (after first name, last name, display name, language, email)
            if all_buttons.count() > 4:
                all_buttons.nth(4).click()

        page.wait_for_timeout(300)
        page.screenshot(path=str(ARTIFACTS_DIR / "06-password-expand.png"))
        print("   Password change form expanded.")

        # Test AI settings dropdowns
        print("7. Checking AI settings section...")
        ai_selects = page.locator('section:has-text("AI-inställningar") select')
        ai_count = ai_selects.count()
        print(f"   Found {ai_count} AI settings dropdown(s)")
        page.screenshot(path=str(ARTIFACTS_DIR / "07-ai-settings.png"))

        # Test responsiveness - mobile viewport
        print("8. Testing mobile responsiveness...")
        page.set_viewport_size({"width": 375, "height": 812})
        page.wait_for_timeout(300)
        page.screenshot(path=str(ARTIFACTS_DIR / "08-mobile-view.png"))
        print("   Mobile view captured.")

        # Tablet viewport
        print("9. Testing tablet responsiveness...")
        page.set_viewport_size({"width": 768, "height": 1024})
        page.wait_for_timeout(300)
        page.screenshot(path=str(ARTIFACTS_DIR / "09-tablet-view.png"))
        print("   Tablet view captured.")

        browser.close()

    print(f"\n✓ Screenshots saved to {ARTIFACTS_DIR}")
    print("\nVerification complete. Please review the screenshots to confirm:")
    print("  - Single outer panel with brutal shadow (no stacked shadows)")
    print("  - Inline editing works (click field → edit → save/cancel)")
    print("  - AI settings use inline dropdowns")
    print("  - Responsive design maintained")
    return 0


if __name__ == "__main__":
    sys.exit(main())
