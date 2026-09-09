from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(f"PAGE ERROR: {err}"))

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)

        print(f"Console errors: {console_errors}")

        # Try clicking with force
        print("\nTrying click with force=True...")
        page.locator('#settingsBtn').click(force=True, timeout=5000)
        page.wait_for_timeout(1000)

        menu_display = page.evaluate("document.getElementById('settingsMenu').style.display")
        menu_visible = page.locator('#settingsMenu').is_visible()
        print(f"Menu display: '{menu_display}', visible: {menu_visible}")

        if menu_visible:
            page.screenshot(path="settings_force.png")
        else:
            # Try JS click directly
            page.evaluate("document.getElementById('settingsBtn').click()")
            page.wait_for_timeout(500)
            menu_display2 = page.evaluate("document.getElementById('settingsMenu').style.display")
            print(f"After JS click: '{menu_display2}'")
            page.screenshot(path="settings_js.png")

        browser.close()
        print("Done!")

run_tests()
