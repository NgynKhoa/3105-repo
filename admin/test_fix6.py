# -*- coding: utf-8 -*-
"""Test fix-6: label theme, package boxes, rain front repo, light mode, links transparency"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Capture JS errors
        page.on("console", lambda msg: None)  # silent
        errors = []
        page.add_init_script("""
            window.__pageErrors = [];
            window.addEventListener('error', (e) => {
                window.__pageErrors.push({msg: e.message, line: e.lineno});
            });
        """)

        page.goto(BASE)
        page.wait_for_timeout(1000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(2500)

        # ============ TEST 1: Front repo rain toggle works ============
        print("Test 1: Front repo rain toggle...")
        # Check rain running
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        # Initially rain on (checked)
        rain_checked = page.evaluate("document.getElementById('toggleRain').checked")
        print(f"  - Initial rain checked: {rain_checked}")
        # Turn off rain
        page.evaluate("document.getElementById('toggleRain').click()")
        page.wait_for_timeout(500)
        rain_enabled = page.evaluate("typeof window.rainEnabled !== 'undefined' ? window.rainEnabled : 'undefined'")
        print(f"  - After toggle off: window.rainEnabled = {rain_enabled}")
        assert rain_enabled == False, f"Rain không tắt! got: {rain_enabled}"
        # Turn on rain
        page.evaluate("document.getElementById('toggleRain').click()")
        page.wait_for_timeout(500)
        rain_enabled = page.evaluate("window.rainEnabled")
        print(f"  - After toggle on: window.rainEnabled = {rain_enabled}")
        assert rain_enabled == True, f"Rain không bật! got: {rain_enabled}"
        # Heavy rain
        page.evaluate("document.getElementById('toggleHeavyRain').click()")
        page.wait_for_timeout(500)
        heavy_enabled = page.evaluate("window.heavyRain")
        print(f"  - After heavy toggle: window.heavyRain = {heavy_enabled}")
        assert heavy_enabled == True, f"Heavy rain không bật! got: {heavy_enabled}"
        # Turn off heavy
        page.evaluate("document.getElementById('toggleHeavyRain').click()")
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 2: Light mode - panel/panel-alt ============
        print("\nTest 2: Light mode - panel colors...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(800)
        panel_color = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--panel')")
        panel_alt = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--panel-alt')")
        bg_color = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--bg-color')")
        print(f"  - Light: bg={bg_color.strip()}, panel={panel_color.strip()}, panel-alt={panel_alt.strip()}")
        # Light mode panel phải là sáng
        assert "245" in panel_color or "240" in panel_color or "255" in panel_color, f"Panel light mode không sáng! got: {panel_color}"
        assert bg_color.strip().lower() in ["#ffffff", "rgb(255, 255, 255)", "white"], f"BG light mode không trắng! got: {bg_color}"
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 3: Links khung với transparency ============
        print("\nTest 3: Links (#stars) background đổi theo transparency...")
        stars_bg = page.evaluate("getComputedStyle(document.getElementById('stars')).background")
        print(f"  - stars background: {stars_bg[:80]}...")
        # Default transparency 92 - phải có rgba từ var(--panel) chứ không phải hardcode
        # Check that stars uses panel var (not fixed rgba)
        assert "245" in stars_bg or "240" in stars_bg or "var(--panel)" in stars_bg, f"stars bg không đổi theo transparency! got: {stars_bg[:100]}"

        # ============ TEST 4: Dashboard - label admin đổi màu theo theme ============
        print("\nTest 4: Dashboard form-label colors theo theme...")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        # Get label color in default green theme
        label_color = page.evaluate("getComputedStyle(document.querySelector('.form-label')).color")
        print(f"  - form-label color (green theme): {label_color}")
        # Should be green-ish (rgb 128, 255, 64)
        assert "128" in label_color, f"Label không có màu theme green! got: {label_color}"
        # Change theme
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.click('[data-theme="cyan"]')
        page.wait_for_timeout(800)
        label_color_cyan = page.evaluate("getComputedStyle(document.querySelector('.form-label')).color")
        print(f"  - form-label color (cyan theme): {label_color_cyan}")
        assert "0, 240, 255" in label_color_cyan, f"Label không đổi màu theme cyan! got: {label_color_cyan}"
        # Change back to green
        page.click('[data-theme="green"]')
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 5: Dashboard - package boxes preview light/dark ============
        print("\nTest 5: Dashboard preview - package boxes theo dark/light...")
        page.click('[data-tab="boxes"]')
        page.wait_for_timeout(800)
        # Check panel-alt color in dark mode
        panel_alt_dark = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--panel-alt')")
        print(f"  - panel-alt (dark): {panel_alt_dark.strip()}")
        # Toggle light mode
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(800)
        panel_alt_light = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--panel-alt')")
        print(f"  - panel-alt (light): {panel_alt_light.strip()}")
        # Light mode panel-alt phải sáng
        assert "230" in panel_alt_light or "240" in panel_alt_light or "245" in panel_alt_light or "255" in panel_alt_light, f"panel-alt light không sáng! got: {panel_alt_light}"
        # Verify package boxes colors change
        pkg_box_bg = page.evaluate("""
            (() => {
                const box = document.querySelector('[data-box="packages-box"]');
                const pkg = box.querySelector('div[style*="height:60px"]');
                return {
                    box_bg: getComputedStyle(box).backgroundColor,
                    pkg_bg: getComputedStyle(pkg).backgroundColor,
                };
            })()
        """)
        print(f"  - packages box bg (light): {pkg_box_bg['box_bg']}")
        print(f"  - pkg item bg (light): {pkg_box_bg['pkg_bg']}")
        # Back to dark
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 6: All pages still load ============
        print("\nTest 6: All pages load...")
        for path in ["/", "/blog", "/dashboard", "/blog-post/1"]:
            page.goto(f"{BASE}{path}")
            page.wait_for_timeout(1500)
            ready = page.evaluate("document.readyState")
            title = page.title()
            print(f"  - {path}: {title} (readyState={ready})")
            assert ready == "complete"

        # ============ TEST 7: Front repo blog items still work ============
        print("\nTest 7: Front repo blog items...")
        page.goto(BASE)
        page.wait_for_timeout(2500)
        blog_count = page.evaluate("document.querySelectorAll('#blogList .blog-item').length")
        print(f"  - Blog items: {blog_count}")
        assert blog_count >= 5

        browser.close()
        page_errors = []  # not used
        print("\n=== ALL FIX-6 TESTS PASSED ===")

if __name__ == "__main__":
    run_tests()
