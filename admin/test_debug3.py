from playwright.sync_api import sync_playwright
import time

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Capture ALL console messages
        page.on("console", lambda msg: print(f"  CONSOLE [{msg.type}]: {msg.text}"))

        page.goto(BASE)
        page.wait_for_timeout(3000)

        # Check if script executed
        result = page.evaluate("""
            () => {
                try {
                    const btn = document.getElementById('settingsBtn');
                    const menu = document.getElementById('settingsMenu');
                    if (!btn) return 'No button';
                    if (!menu) return 'No menu';
                    return 'Found: btn=' + btn.tagName + ', menu=' + menu.tagName;
                } catch(e) {
                    return 'Error: ' + e.message;
                }
            }
        """)
        print(f"Elements: {result}")

        # Try using Playwright's native click
        print("\nTrying page.locator('#settingsBtn').click()...")
        page.locator('#settingsBtn').click(timeout=5000)
        page.wait_for_timeout(500)
        menu_display = page.evaluate("document.getElementById('settingsMenu').style.display")
        print(f"Menu display after Playwright click: '{menu_display}'")
        page.screenshot(path="debug_playwright.png", full_page=False)

        browser.close()
        print("\nDone!")

run_tests()
