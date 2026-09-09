from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        page.goto(BASE)
        page.wait_for_timeout(3000)

        # Check for errors
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        # Hard reload
        page.goto(BASE + "/", wait_until="networkidle")
        page.wait_for_timeout(2000)

        print(f"Errors: {errors}")

        # Click settings
        page.locator('#settingsBtn').click(timeout=5000)
        page.wait_for_timeout(500)

        menu_display = page.evaluate("document.getElementById('settingsMenu').style.display")
        print(f"Menu display: '{menu_display}'")

        if menu_display == 'block':
            page.screenshot(path="settings_ok.png")
            print("SUCCESS!")
        else:
            # Check for errors again
            print(f"Errors after click: {errors}")
            # Try to see what line has the error
            script_check = page.evaluate("""
                () => {
                    const scripts = document.querySelectorAll('script');
                    let result = '';
                    scripts.forEach((s, i) => {
                        try {
                            new Function(s.textContent);
                        } catch(e) {
                            result += `Script ${i}: ${e.message}\\n`;
                        }
                    });
                    return result || 'All scripts OK';
                }
            """)
            print(f"Script check: {script_check}")

        browser.close()

run_tests()
