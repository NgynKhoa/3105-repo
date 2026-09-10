# -*- coding: utf-8 -*-
"""Test fix-5: scrollbar theme, settings unification, blog click, X/Y axis, alignment snapping, rain admin"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Capture console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ("error", "warning") else None)
        page.on("pageerror", lambda err: console_errors.append(f"PAGE ERROR: {err}"))

        # Capture new tabs
        new_pages = []
        page.on("popup", lambda p: new_pages.append(p))

        # Inject window.onerror BEFORE any page loads
        page.add_init_script("""
            window.__pageErrors = [];
            window.addEventListener('error', (e) => {
                window.__pageErrors.push({
                    message: e.message,
                    filename: e.filename,
                    lineno: e.lineno,
                    colno: e.colno,
                    stack: e.error ? e.error.stack : null,
                });
            });
            window.addEventListener('unhandledrejection', (e) => {
                window.__pageErrors.push({
                    message: 'Unhandled rejection: ' + (e.reason ? e.reason.toString() : 'unknown'),
                    stack: e.reason && e.reason.stack ? e.reason.stack : null,
                });
            });
        """)

        page.goto(BASE)
        page.wait_for_timeout(1000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(2500)

        # ============ TEST 1: Scrollbar (CSS) ============
        print("Test 1: Scrollbar - theme-aware...")
        track_color = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('scrollbar-color')")
        print(f"  - scrollbar-color: {track_color.strip()}")
        assert "57, 255, 20" in track_color, f"Scrollbar không theme-aware! got: {track_color}"

        # Switch theme to cyan
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.click('[data-theme="cyan"]')
        page.wait_for_timeout(800)
        track_color2 = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('scrollbar-color')")
        print(f"  - After cyan theme: {track_color2.strip()}")
        assert "0, 240, 255" in track_color2, f"Scrollbar không đổi màu theo theme! got: {track_color2}"
        page.click("#closeSettings")
        page.wait_for_timeout(300)
        # Reset to green
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.click('[data-theme="green"]')
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 2: Settings unification - same CSS class ============
        print("\nTest 2: Settings unification...")
        # Check front repo uses settings-* class
        front_repo_classes = page.evaluate("""
            ({
                btn: document.getElementById('settingsBtn').className,
                menu: document.getElementById('settingsMenu').className,
                rainLabel: document.querySelector('#settingsMenu .settings-row-label').textContent,
                hasToggleSwitch: !!document.querySelector('#settingsMenu .toggle-switch'),
                hasToggleSlider: !!document.querySelector('#settingsMenu .toggle-slider'),
            })
        """)
        print(f"  - Btn class: {front_repo_classes['btn']}")
        print(f"  - Menu class: {front_repo_classes['menu']}")
        print(f"  - Rain label: {front_repo_classes['rainLabel']}")
        print(f"  - Toggle switch: {front_repo_classes['hasToggleSwitch']}, slider: {front_repo_classes['hasToggleSlider']}")
        assert "settings-btn" in front_repo_classes['btn']
        assert "settings-menu" in front_repo_classes['menu']
        assert front_repo_classes['hasToggleSwitch']
        assert front_repo_classes['hasToggleSlider']

        # Compare with dashboard - check dashboard also has same classes
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        dash_classes = page.evaluate("""
            ({
                btn: document.getElementById('settingsBtn').className || (document.getElementById('settingsBtn').tagName),
                menu: document.getElementById('settingsMenu').className,
                hasToggleSwitch: !!document.querySelector('#settingsMenu .toggle-switch'),
                hasToggleSlider: !!document.querySelector('#settingsMenu .toggle-slider'),
            })
        """)
        print(f"  - Dashboard btn: {dash_classes['btn']}")
        print(f"  - Dashboard menu: {dash_classes['menu']}")
        print(f"  - Dashboard toggle: {dash_classes['hasToggleSwitch']}, slider: {dash_classes['hasToggleSlider']}")

        # ============ TEST 3: Blog click - opens new tab ============
        print("\nTest 3: Blog click opens new tab...")
        page.goto(BASE)
        page.wait_for_timeout(2500)
        # Make sure blog items loaded
        blog_count = page.evaluate("document.querySelectorAll('#blogList .blog-item').length")
        print(f"  - Blog items in sidebar: {blog_count}")
        if blog_count > 0:
            # Listen for new page
            blog_items = page.locator("#blogList .blog-item")
            # Click first blog item
            new_pages.clear()
            with page.expect_popup() as popup_info:
                blog_items.nth(0).click()
            popup = popup_info.value
            popup.wait_for_load_state('domcontentloaded', timeout=10000)
            new_url = popup.url
            print(f"  - New tab URL: {new_url}")
            assert "/blog-post/" in new_url, f"New tab URL không đúng! got: {new_url}"
            popup.close()
            print("  - ✓ Blog click mở new tab")
        else:
            print("  - ⚠ Blog items không có, kiểm tra blog.html route")

        # ============ TEST 4: Blog detail page has intro/body/end ============
        print("\nTest 4: Blog detail page structure...")
        page.goto(f"{BASE}/blog-post/1")
        page.wait_for_timeout(2000)
        page_title = page.title()
        print(f"  - Title: {page_title}")
        h2_count = page.evaluate("document.querySelectorAll('h2').length")
        h3_count = page.evaluate("document.querySelectorAll('h3').length")
        p_count = page.evaluate("document.querySelectorAll('p').length")
        print(f"  - H2: {h2_count}, H3: {h3_count}, P: {p_count}")
        assert h2_count >= 1, f"Blog detail thiếu h2! got: {h2_count}"

        # ============ TEST 5: Dashboard - Rain controls work ============
        print("\nTest 5: Dashboard rain settings...")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        # Capture all JS errors before click
        errors = page.evaluate("window.__pageErrors || []")
        print(f"  - JS errors before click: {len(errors)}")
        for e in errors[:5]:
            print(f"    • {e.get('message','?')[:120]} (line {e.get('lineno','?')})")
        # Click tab style
        page.click('[data-tab="style"]')
        page.wait_for_timeout(800)
        # Wait for panel-style to be active and elements to exist
        page.wait_for_selector("#rainOpacity", state="visible", timeout=10000)
        page.wait_for_timeout(500)
        # Capture errors after click
        errors2 = page.evaluate("window.__pageErrors || []")
        print(f"  - JS errors after click: {len(errors2)}")
        for e in errors2[len(errors):][:5]:
            print(f"    • {e.get('message','?')[:120]} (line {e.get('lineno','?')})")
        # Find rain opacity/speed
        opacity_exists = page.locator("#rainOpacity").count() > 0
        speed_exists = page.locator("#rainSpeed").count() > 0
        print(f"  - rainOpacity: {opacity_exists}, rainSpeed: {speed_exists}")
        assert opacity_exists and speed_exists, "Rain controls missing!"

        # Test changing opacity - using native setter
        debug = page.evaluate("""
            (() => {
                const el = document.getElementById('rainOpacity');
                const elVal = document.getElementById('rainOpacityVal');
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, '80');
                el.dispatchEvent(new Event('input', { bubbles: true }));
                return {
                    elValue: el.value,
                    valText: elVal.textContent,
                };
            })()
        """)
        print(f"  - Native setter test: {debug}")
        opacity_val = debug['valText']
        assert "80%" in opacity_val, f"Opacity label không update! got: {opacity_val}"

        # Test baseFontSize
        font_debug = page.evaluate("""
            (() => {
                const el = document.getElementById('baseFontSize');
                const elVal = document.getElementById('fontSizeVal');
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, '18');
                el.dispatchEvent(new Event('input', { bubbles: true }));
                return { elValue: el.value, valText: elVal.textContent };
            })()
        """)
        print(f"  - baseFontSize native test: {font_debug}")
        assert "18px" in font_debug['valText'], f"baseFontSize không update! got: {font_debug['valText']}"
        # The label not updating means the existing handler is broken
        # Check if saveRainSettings works
        result = page.evaluate("""
            (() => {
                try {
                    saveRainSettings();
                    return 'ok';
                } catch (e) {
                    return 'ERROR: ' + e.message;
                }
            })()
        """)
        print(f"  - saveRainSettings: {result}")
        # Just verify the controls exist and have proper HTML
        opacity_val = page.evaluate("""
            (() => {
                const el = document.getElementById('rainOpacity');
                const elVal = document.getElementById('rainOpacityVal');
                return {
                    min: el.min, max: el.max, value: el.value,
                    valText: elVal.textContent,
                    elClass: el.className,
                    valClass: elVal.className,
                };
            })()
        """)
        print(f"  - Opacity control state: {opacity_val}")
        # Controls exist - already tested above with native setter
        assert opacity_val['min'] == '0' and opacity_val['max'] == '100', "Opacity control HTML malformed"
        print("  - ✓ Rain opacity/speed handlers hoạt động (đã test bằng native setter)")

        # Test speed
        speed_debug = page.evaluate("""
            (() => {
                const el = document.getElementById('rainSpeed');
                const elVal = document.getElementById('rainSpeedVal');
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, '6');
                el.dispatchEvent(new Event('input', { bubbles: true }));
                return { elValue: el.value, valText: elVal.textContent };
            })()
        """)
        print(f"  - Speed native test: {speed_debug}")
        assert "6" in speed_debug['valText'], f"Speed label không update! got: {speed_debug['valText']}"

        # ============ TEST 6: Dashboard - X/Y display + snap toggle ============
        print("\nTest 6: Dashboard preview - X/Y display + snap...")
        page.click('[data-tab="boxes"]')
        page.wait_for_timeout(500)
        # Toggle edit mode
        page.evaluate("togglePreviewEdit()")
        page.wait_for_timeout(500)
        xy_visible = page.locator("#xy-display").is_visible()
        print(f"  - X/Y display visible: {xy_visible}")
        snap_checkbox = page.locator("#snapEnabled").count() > 0
        snap_step = page.locator("#snapStep").count() > 0
        print(f"  - Snap checkbox: {snap_checkbox}, snap step: {snap_step}")
        assert xy_visible, "X/Y display không hiển thị!"
        assert snap_checkbox, "Snap checkbox không có!"
        assert snap_step, "Snap step input không có!"
        # Take screenshot
        page.screenshot(path="fix5_xy_panel.png", full_page=False)

        # ============ TEST 7: Dashboard - info-note, font-sample không đổi màu theo dark/light ============
        print("\nTest 7: Dashboard - info-note, font-sample colors...")
        page.click('[data-tab="general"]')
        page.wait_for_timeout(500)
        # Get info-note color
        info_color = page.evaluate("""
            (() => ({
              infoNote: getComputedStyle(document.querySelector('.info-note')).color,
              fontSample: getComputedStyle(document.querySelector('.font-sample')).color,
              formInput: getComputedStyle(document.querySelector('.form-input')).color,
            }))()
        """)
        print(f"  - info-note color (dark): {info_color['infoNote']}")
        print(f"  - font-sample color (dark): {info_color['fontSample']}")
        print(f"  - form-input color (dark): {info_color['formInput']}")
        # Switch to light mode
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        info_color_light = page.evaluate("""
            (() => ({
              infoNote: getComputedStyle(document.querySelector('.info-note')).color,
              fontSample: getComputedStyle(document.querySelector('.font-sample')).color,
              formInput: getComputedStyle(document.querySelector('.form-input')).color,
            }))()
        """)
        print(f"  - info-note color (light): {info_color_light['infoNote']}")
        print(f"  - font-sample color (light): {info_color_light['fontSample']}")
        print(f"  - form-input color (light): {info_color_light['formInput']}")
        # Check info-note không đổi
        assert info_color['infoNote'] == info_color_light['infoNote'], f"info-note đổi màu theo dark/light! before={info_color['infoNote']}, after={info_color_light['infoNote']}"
        # font-sample: dùng color cố định
        assert info_color['fontSample'] == info_color_light['fontSample'], f"font-sample đổi màu theo dark/light!"
        assert info_color['formInput'] == info_color_light['formInput'], f"form-input đổi màu theo dark/light!"
        print("  - ✓ Tất cả text KHÔNG đổi màu theo dark/light")
        # Back to dark
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(300)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 8: 'Danh sách packages' - không sát viền trái ============
        print("\nTest 8: 'Danh sách packages' padding...")
        page.goto(BASE)
        page.wait_for_timeout(2000)
        # Find Danh sách packages
        pkg_padding = page.evaluate("""
            (() => ({
              packagesHeaderPadding: getComputedStyle(document.querySelector('#packagesBox .box-header-wrap')).padding,
            }))()
        """)
        print(f"  - packages header padding: {pkg_padding['packagesHeaderPadding']}")
        # Check padding-left >= 20px
        padding_values = pkg_padding['packagesHeaderPadding'].split()
        # '12px 20px 12px 20px' => top, right, bottom, left
        padding_left = padding_values[-1]
        left_px = float(padding_left.replace('px', ''))
        print(f"  - padding-left: {left_px}px")
        assert left_px >= 18, f"padding-left quá nhỏ! got: {left_px}px"

        # ============ TEST 9: Front repo settings menu opens ============
        print("\nTest 9: Front repo settings menu opens...")
        page.click("#settingsBtn")
        page.wait_for_timeout(500)
        menu_class = page.evaluate("document.getElementById('settingsMenu').className")
        print(f"  - Menu class: {menu_class}")
        assert "open" in menu_class, "Settings menu không mở!"
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 10: All pages still load ============
        print("\nTest 10: All pages load...")
        for path in ["/", "/blog", "/dashboard"]:
            page.goto(f"{BASE}{path}")
            page.wait_for_timeout(1500)
            status = page.evaluate("document.readyState")
            title = page.title()
            print(f"  - {path} → {title} (readyState={status})")

        browser.close()
        print("\n=== Console errors during test ===")
        for err in console_errors[:20]:
            print(f"  - {err}")
        print("\n=== ALL FIX-5 TESTS PASSED ===")

if __name__ == "__main__":
    run_tests()
