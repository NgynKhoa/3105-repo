# -*- coding: utf-8 -*-
"""Test fix-9: select option visible in light mode; label/repoSelect back to dark when toggling"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # ==== Front repo test ====
    page.goto(BASE + "?_=fr1")
    page.wait_for_timeout(2000)
    page.evaluate("localStorage.clear()")
    page.goto(BASE + "?_=fr2")
    page.wait_for_timeout(2500)

    # Front repo: open modal with "Sửa" first button
    sua_btns = page.query_selector_all("button")
    for b in sua_btns:
        txt = b.text_content().strip()
        if txt == "Sửa":
            b.click()
            break
    page.wait_for_timeout(800)

    # Check dark mode input bg
    info_dark = page.evaluate("""
        (() => {
            const r = {};
            const ids = ['meta_identifier', 'meta_name', 'meta_accentColor', 'meta_description', 'repoSelect', 'meta_icon'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) {
                    const cs = getComputedStyle(el);
                    r[id] = {bg: cs.backgroundColor, color: cs.color};
                }
            }
            // Check option bg
            const sel = document.getElementById('primaryFont') || document.querySelector('select');
            if (sel) {
                const opt = sel.querySelector('option');
                if (opt) {
                    r['_option_bg'] = getComputedStyle(opt).backgroundColor;
                    r['_option_color'] = getComputedStyle(opt).color;
                }
            }
            // Label colors
            const label = document.querySelector('label[for="meta_name"]');
            if (label) r['_label_meta_name'] = getComputedStyle(label).color;
            return r;
        })()
    """)
    print("=== Front repo DARK MODE ===")
    for k, v in info_dark.items(): print(f"  {k}: {v}")

    # Toggle light mode
    page.click("#settingsBtn")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(500)
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    info_light = page.evaluate("""
        (() => {
            const r = {};
            const ids = ['meta_identifier', 'meta_name', 'meta_accentColor', 'meta_description', 'repoSelect', 'meta_icon'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) {
                    const cs = getComputedStyle(el);
                    r[id] = {bg: cs.backgroundColor, color: cs.color};
                }
            }
            const sel = document.querySelector('select');
            if (sel) {
                const opt = sel.querySelector('option');
                if (opt) {
                    r['_option_bg'] = getComputedStyle(opt).backgroundColor;
                    r['_option_color'] = getComputedStyle(opt).color;
                }
            }
            return r;
        })()
    """)
    print("\n=== Front repo LIGHT MODE ===")
    for k, v in info_light.items(): print(f"  {k}: {v}")

    # Toggle back to dark
    page.click("#settingsBtn")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(500)
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    info_dark2 = page.evaluate("""
        (() => {
            const r = {};
            const ids = ['meta_identifier', 'meta_name', 'meta_accentColor', 'meta_description', 'repoSelect'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) r[id] = getComputedStyle(el).backgroundColor;
            }
            return r;
        })()
    """)
    print("\n=== Front repo BACK TO DARK ===")
    for k, v in info_dark2.items(): print(f"  {k}: {v}")
    for k, v in info_dark2.items():
        if "255, 255, 255" in v:
            print(f"  FAIL: {k} still light after toggle back!")

    # ==== Dashboard ====
    print("\n\n=== Dashboard TEST ===")
    page.goto(f"{BASE}/dashboard?_=d1")
    page.wait_for_timeout(2500)

    sel_info_dark = page.evaluate("""
        (() => {
            const r = {};
            const sel = document.getElementById('primaryFont');
            if (sel) {
                r['_input_bg'] = getComputedStyle(sel).backgroundColor;
                r['_input_color'] = getComputedStyle(sel).color;
                const opt = sel.querySelector('option');
                if (opt) {
                    r['_option_bg'] = getComputedStyle(opt).backgroundColor;
                    r['_option_color'] = getComputedStyle(opt).color;
                }
            }
            return r;
        })()
    """)
    print("Dashboard DARK (select):")
    for k, v in sel_info_dark.items(): print(f"  {k}: {v}")

    page.click("#settingsBtn")
    page.wait_for_timeout(300)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(500)
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    sel_info_light = page.evaluate("""
        (() => {
            const r = {};
            const sel = document.getElementById('primaryFont');
            if (sel) {
                r['_input_bg'] = getComputedStyle(sel).backgroundColor;
                r['_input_color'] = getComputedStyle(sel).color;
                const opt = sel.querySelector('option');
                if (opt) {
                    r['_option_bg'] = getComputedStyle(opt).backgroundColor;
                    r['_option_color'] = getComputedStyle(opt).color;
                }
            }
            return r;
        })()
    """)
    print("Dashboard LIGHT (select):")
    for k, v in sel_info_light.items(): print(f"  {k}: {v}")

    # Visual check - take screenshot
    page.screenshot(path="c:/Users/NK/Desktop/MOD/3105-repo/admin/fix9_dash_light.png", full_page=True)

    browser.close()
    print("\n=== DONE ===")
