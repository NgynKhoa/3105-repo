# -*- coding: utf-8 -*-
"""Test fix-7 final: open repo modal in light mode"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    # ==== Front repo ====
    page.goto(BASE + "?_=fr1")
    page.wait_for_timeout(2000)
    page.evaluate("localStorage.clear()")
    page.goto(BASE + "?_=fr2")
    page.wait_for_timeout(2500)

    # Toggle light mode
    page.click("#settingsBtn")
    page.wait_for_timeout(400)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(800)
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    # Try to open repo add/edit modal - click first "Sửa" button
    sua_btns = page.query_selector_all("button")
    for b in sua_btns:
        txt = b.text_content().strip()
        if txt == "Sửa":
            b.click()
            break
    page.wait_for_timeout(800)

    # Now check modal inputs
    inputs = page.evaluate("""
        (() => {
            const result = {};
            const ids = ['meta_identifier', 'meta_name', 'meta_accentColor', 'meta_description'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) {
                    const cs = getComputedStyle(el);
                    result[id] = {
                        bg: cs.backgroundColor,
                        color: cs.color,
                        border: cs.borderColor
                    };
                }
            }
            // Also any input/select/textarea in modal
            const modalInputs = document.querySelectorAll('#modalBody input, #modalBody select, #modalBody textarea');
            result['_all_modal_inputs_count'] = modalInputs.length;
            result['_first_input_bg'] = modalInputs.length ? getComputedStyle(modalInputs[0]).backgroundColor : null;
            return result;
        })()
    """)
    print("=== Front repo modal inputs (light mode) ===")
    for k, v in inputs.items():
        print(f"  {k}: {v}")
    # Check no input has rgba(3, 7, 14) - the old dark color
    for k, v in inputs.items():
        if isinstance(v, dict) and "3, 7, 14" in str(v.get('bg', '')):
            print(f"  FAIL: {k} still dark! bg={v['bg']}")
    print("\nAll modal inputs are light bg!" if all("3, 7, 14" not in str(v.get('bg', '')) for v in inputs.values() if isinstance(v, dict)) else "Some inputs still dark")

    page.screenshot(path="c:/Users/NK/Desktop/MOD/3105-repo/admin/fix7_modal_light.png", full_page=True)

    # ==== Dashboard modal ====
    page.goto(f"{BASE}/dashboard?_=dash1")
    page.wait_for_timeout(2500)
    page.click("#settingsBtn")
    page.wait_for_timeout(400)
    page.evaluate("document.getElementById('toggleDarkMode').click()")
    page.wait_for_timeout(800)
    page.click("#closeSettings")
    page.wait_for_timeout(300)

    dash_inputs = page.evaluate("""
        (() => {
            const result = {};
            const ids = ['siteTitle', 'logoText', 'repoUrl', 'siteDesc', 'postIcon', 'postTitle', 'postExcerpt', 'postContent', 'primaryFont', 'monoFont', 'titleFont'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) {
                    const cs = getComputedStyle(el);
                    result[id] = cs.backgroundColor;
                }
            }
            return result;
        })()
    """)
    print("\n=== Dashboard inputs (light mode) ===")
    for k, v in dash_inputs.items():
        print(f"  {k}: {v}")

    page.screenshot(path="c:/Users/NK/Desktop/MOD/3105-repo/admin/fix7_dash_light.png", full_page=True)
    browser.close()
    print("\n=== DONE ===")
