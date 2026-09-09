from playwright.sync_api import sync_playwright
import time

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Test: Home page
        print("Test: Home page...")
        page.goto(BASE)
        page.wait_for_timeout(3000)
        page.screenshot(path="debug1_home.png", full_page=False)

        # Check if settingsBtn exists and click via JS
        print("\nDebug settings menu...")

        # Check if event listener is attached
        has_listener = page.evaluate("""
            () => {
                const btn = document.getElementById('settingsBtn');
                if (!btn) return 'No button';
                // Check if click event is set
                const listeners = btn.getEventListeners ? btn.getEventListeners('click') : null;
                return btn ? 'Button found, onclick: ' + btn.onclick : 'No button';
            }
        """)
        print(f"  - Button status: {has_listener}")

        # Try clicking via JS
        result = page.evaluate("""
            () => {
                const btn = document.getElementById('settingsBtn');
                const menu = document.getElementById('settingsMenu');
                const overlay = document.getElementById('settingsOverlay');
                if (btn) btn.click();
                return {
                    menuDisplay: menu ? menu.style.display : 'no menu',
                    overlayDisplay: overlay ? overlay.style.display : 'no overlay'
                };
            }
        """)
        print(f"  - After JS click: {result}")
        page.wait_for_timeout(500)
        page.screenshot(path="debug2_after_js.png", full_page=False)

        # Check if menu is visible
        menu_visible = page.locator("#settingsMenu").is_visible()
        print(f"  - Menu visible after JS click: {menu_visible}")

        # Try directly setting display
        page.evaluate("""
            () => {
                const menu = document.getElementById('settingsMenu');
                if (menu) {
                    menu.style.display = 'block';
                    menu.style.position = 'fixed';
                    menu.style.top = '60px';
                    menu.style.right = '14px';
                    menu.style.zIndex = '10001';
                    menu.style.width = '260px';
                    menu.style.background = 'var(--panel)';
                    menu.style.border = '1px solid var(--border)';
                    menu.style.borderRadius = '14px';
                    menu.style.boxShadow = 'var(--shadow)';
                    menu.style.overflow = 'hidden';
                }
            }
        """)
        page.wait_for_timeout(500)
        menu_visible = page.locator("#settingsMenu").is_visible()
        print(f"  - Menu visible after direct style set: {menu_visible}")
        page.screenshot(path="debug3_after_style.png", full_page=False)

        # Now try theme button
        theme_btn = page.locator('[data-theme="pink"]').is_visible()
        print(f"  - Pink theme btn visible: {theme_btn}")
        if theme_btn:
            page.click('[data-theme="pink"]')
            page.wait_for_timeout(500)
            page.screenshot(path="debug4_pink.png", full_page=False)

        browser.close()
        print("\nDone!")

run_tests()
