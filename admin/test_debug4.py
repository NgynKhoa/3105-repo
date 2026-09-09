from playwright.sync_api import sync_playwright
import time

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto(BASE)
        page.wait_for_timeout(3000)

        # Inject a test click handler to see if events fire
        page.evaluate("""
            () => {
                const btn = document.getElementById('settingsBtn');
                btn.addEventListener('click', function(e) {
                    console.log('Click event fired on button!');
                    const menu = document.getElementById('settingsMenu');
                    menu.style.display = 'block';
                    console.log('Menu display set to block');
                });
            }
        """)

        print("Clicking settings button...")
        page.locator('#settingsBtn').click()
        page.wait_for_timeout(1000)

        menu_display = page.evaluate("document.getElementById('settingsMenu').style.display")
        print(f"Menu display: '{menu_display}'")

        # Check for errors
        print("Done!")

run_tests()
