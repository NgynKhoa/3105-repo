from playwright.sync_api import sync_playwright
import time

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto(BASE)
        page.wait_for_timeout(3000)

        # Just use Playwright's native click
        print("Clicking settings button (native)...")
        page.locator('#settingsBtn').click(timeout=5000)
        page.wait_for_timeout(1000)

        menu_display = page.evaluate("document.getElementById('settingsMenu').style.display")
        menu_visible = page.locator('#settingsMenu').is_visible()
        print(f"Menu display: '{menu_display}', visible: {menu_visible}")

        if menu_visible:
            page.screenshot(path="settings_open.png")
            # Click theme pink
            page.click('[data-theme="pink"]')
            page.wait_for_timeout(500)
            page.screenshot(path="pink_theme.png")
            print("Pink theme applied!")

        browser.close()
        print("Done!")

run_tests()
