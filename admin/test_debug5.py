from playwright.sync_api import sync_playwright
import time

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        # Check if script block is loaded
        result = page.evaluate("""
            () => {
                const script = document.querySelector('script:last-of-type');
                if (script) return script.textContent.substring(0, 500);
                return 'No script';
            }
        """)
        print(f"Last script (first 500 chars): {result}")

        # Check settingsBtn handler
        result2 = page.evaluate("""
            () => {
                const btn = document.getElementById('settingsBtn');
                const events = getEventListeners ? getEventListeners(btn) : null;
                return events ? Object.keys(events).join(', ') : 'No events (getEventListeners unavailable)';
            }
        """)
        print(f"Events on settingsBtn: {result2}")

        # Try dispatchEvent
        result3 = page.evaluate("""
            () => {
                const btn = document.getElementById('settingsBtn');
                const menu = document.getElementById('settingsMenu');
                btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                return menu.style.display;
            }
        """)
        print(f"Menu display after dispatchEvent: {result3}")

        browser.close()
        print("Done!")

run_tests()
