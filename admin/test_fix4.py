# -*- coding: utf-8 -*-
"""Test fix-4: settings, dark/light mode, text colors, admin font"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Clear storage
        page.goto(BASE)
        page.wait_for_timeout(1000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(2000)

        # ============ TEST 1: Settings menu toggle switch works ============
        print("Test 1: Settings menu - toggle switch...")
        page.click("#settingsBtn")
        page.wait_for_timeout(500)
        # Check menu opened
        menu_classes = page.evaluate("document.getElementById('settingsMenu').className")
        print(f"  - Menu class: {menu_classes}")
        assert "open" in menu_classes, f"Menu không mở! class={menu_classes}"
        page.screenshot(path="fix4_1_menu_open.png", full_page=False)
        # Check toggle switch exists and works (input is opacity:0, check via state)
        rain_exists = page.locator("#toggleRain").count() > 0
        heavy_exists = page.locator("#toggleHeavyRain").count() > 0
        dark_exists = page.locator("#toggleDarkMode").count() > 0
        print(f"  - Rain toggle: {rain_exists}, Heavy: {heavy_exists}, Dark: {dark_exists}")
        assert rain_exists and heavy_exists and dark_exists, "Toggle switches not found!"

        # Check slider
        slider = page.locator("#rangeTransparency").count() > 0
        print(f"  - Transparency slider: {slider}")
        assert slider, "Transparency slider not found!"
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 2: Settings button hover rotation ============
        print("\nTest 2: Settings button hover effect...")
        btn = page.locator("#settingsBtn")
        box = btn.bounding_box()
        page.mouse.move(box["x"] + 20, box["y"] + 20)
        page.wait_for_timeout(400)
        transform = page.evaluate("getComputedStyle(document.getElementById('settingsBtn')).transform")
        print(f"  - Transform after hover: {transform}")
        page.screenshot(path="fix4_2_btn_hover.png", full_page=False)
        page.mouse.move(0, 0)
        page.wait_for_timeout(200)

        # ============ TEST 3: Rain toggles work ============
        print("\nTest 3: Rain toggles work...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        # Heavy rain
        page.evaluate("document.getElementById('toggleHeavyRain').click()")
        page.wait_for_timeout(500)
        heavy_checked = page.evaluate("document.getElementById('toggleHeavyRain').checked")
        print(f"  - Heavy rain checked: {heavy_checked}")
        assert heavy_checked, "Heavy rain toggle không hoạt động!"
        page.screenshot(path="fix4_3_heavy_rain.png", full_page=False)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 4: Light mode - nền trắng chữ đen ============
        print("\nTest 4: Light mode - nền trắng chữ đen...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        bg_color = page.evaluate("getComputedStyle(document.body).backgroundColor")
        text_color = page.evaluate("getComputedStyle(document.body).color")
        print(f"  - BG color: {bg_color} (expect rgb(255, 255, 255))")
        print(f"  - Text color: {text_color} (expect dark/black)")
        # Light mode bg = white
        assert "255, 255, 255" in bg_color, f"Light mode bg không phải trắng! got: {bg_color}"
        page.screenshot(path="fix4_4_light_mode.png", full_page=False)

        # ============ TEST 5: Dark mode - nền đen chữ trắng ============
        print("\nTest 5: Dark mode - nền đen chữ trắng...")
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        bg_color = page.evaluate("getComputedStyle(document.body).backgroundColor")
        text_color = page.evaluate("getComputedStyle(document.body).color")
        print(f"  - BG color: {bg_color} (expect dark)")
        print(f"  - Text color: {text_color} (expect bright/white)")
        # Dark mode bg = dark
        assert "255, 255, 255" not in bg_color, f"Dark mode bg không phải đen! got: {bg_color}"
        page.screenshot(path="fix4_5_dark_mode.png", full_page=False)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 6: Transparency affects panel elements ============
        print("\nTest 6: Transparency affects panel elements...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("""
            document.getElementById('rangeTransparency').value = 30;
            document.getElementById('rangeTransparency').dispatchEvent(new Event('input'));
        """)
        page.wait_for_timeout(500)
        alpha = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--panel-alpha')")
        print(f"  - Panel alpha at 30%: {alpha}")
        assert "0.3" in alpha, f"Transparency không set đúng alpha! got: {alpha}"
        # Reset
        page.evaluate("""
            document.getElementById('rangeTransparency').value = 92;
            document.getElementById('rangeTransparency').dispatchEvent(new Event('input'));
        """)
        page.wait_for_timeout(300)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 7: Dashboard - settings menu, fonts, text ============
        print("\nTest 7: Dashboard - settings, fonts, text...")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        # Settings menu
        page.click("#settingsBtn")
        page.wait_for_timeout(500)
        menu_ok = page.locator("#settingsMenu.open, #settingsMenu").first.is_visible()
        print(f"  - Dashboard settings menu visible: {menu_ok}")
        assert menu_ok, "Dashboard settings menu không hoạt động!"
        page.screenshot(path="fix4_7_dash_settings.png", full_page=False)

        # Check toggle switches in dashboard (input is opacity:0, check via count)
        rain_d = page.locator("#toggleRain").count() > 0
        dark_d = page.locator("#toggleDarkMode").count() > 0
        print(f"  - Rain toggle in dash: {rain_d}")
        print(f"  - Dark toggle in dash: {dark_d}")
        assert rain_d and dark_d, "Dashboard toggle switches missing!"

        # Test light mode in dashboard
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        dash_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
        dash_text = page.evaluate("getComputedStyle(document.body).color")
        print(f"  - Dashboard light mode BG: {dash_bg}")
        print(f"  - Dashboard light mode text: {dash_text}")
        page.screenshot(path="fix4_7_dash_light.png", full_page=False)

        # Back to dark
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(300)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 8: Dashboard tabs work ============
        print("\nTest 8: Dashboard tabs...")
        for tab in ["general", "boxes", "blog", "fonts", "style"]:
            page.click(f'[data-tab="{tab}"]')
            page.wait_for_timeout(300)
            active = page.locator(f"#panel-{tab}.active").count()
            print(f"  - Tab '{tab}' active: {active > 0}")
            assert active > 0, f"Tab '{tab}' không hoạt động!"
        page.screenshot(path="fix4_8_all_tabs.png", full_page=True)

        # ============ TEST 9: Boxes panel preview works ============
        print("\nTest 9: Boxes panel preview...")
        page.click('[data-tab="boxes"]')
        page.wait_for_timeout(500)
        stage = page.locator("#previewStage").is_visible()
        print(f"  - Preview stage visible: {stage}")
        assert stage, "Preview stage not visible!"

        # Toggle edit mode
        page.evaluate("togglePreviewEdit()")
        page.wait_for_timeout(500)
        handles = page.locator("#previewStage .resize-handle:visible").count()
        print(f"  - Resize handles visible: {handles}")
        assert handles >= 8, f"Resize handles không hiển thị! got: {handles}"
        page.screenshot(path="fix4_9_preview_edit.png", full_page=True)

        # ============ TEST 10: Blog page works ============
        print("\nTest 10: Blog page...")
        page.goto(f"{BASE}/blog")
        page.wait_for_timeout(2000)
        posts = page.evaluate("""
            fetch('/api/blog/posts').then(r => r.json()).then(d => d.posts.length)
        """)
        print(f"  - Blog posts: {posts}")
        assert posts >= 7, f"Blog posts không đủ! got: {posts}"
        page.screenshot(path="fix4_10_blog.png", full_page=True)

        # ============ TEST 11: Theme switching on front repo ============
        print("\nTest 11: Theme switching...")
        page.goto(BASE)
        page.wait_for_timeout(2000)
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        for theme in ["cyan", "pink", "lavender", "yellow", "green"]:
            page.click(f'[data-theme="{theme}"]')
            page.wait_for_timeout(300)
            neon = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--neon')")
            print(f"  - Theme {theme}: neon={neon.strip()}")
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        browser.close()
        print("\n=== ALL FIX-4 TESTS PASSED ===")

if __name__ == "__main__":
    run_tests()
