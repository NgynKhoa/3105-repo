from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Clear localStorage
        page.goto(BASE)
        page.wait_for_timeout(1000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(2000)

        # Test: Toggle dark mode using JS click on toggle-switch label
        print("Test: Dark mode toggle via JS...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        # Use JS to toggle the checkbox and trigger change
        page.evaluate("""
            var cb = document.getElementById('toggleDarkMode');
            cb.checked = false;
            cb.dispatchEvent(new Event('change'));
        """)
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(500)
        page.screenshot(path="final_light_mode.png", full_page=False)
        print(f"  - Light mode applied")

        # Back to dark
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("""
            var cb = document.getElementById('toggleDarkMode');
            cb.checked = true;
            cb.dispatchEvent(new Event('change'));
        """)
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(500)
        page.screenshot(path="final_dark_mode.png", full_page=False)
        print(f"  - Dark mode restored")

        browser.close()
        print("Done!")

run_tests()
