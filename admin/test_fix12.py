# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    # ====== Test 1: Boxes Preview transparency (dashboard) ======
    print('=== [1] Dashboard Boxes Preview transparency ===')
    page.goto(f'{BASE}/dashboard?_=p1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(f'{BASE}/dashboard?_=p2')
    page.wait_for_timeout(2500)

    # Get preview boxes bg in dark
    dark_boxes = page.evaluate('''
        (() => {
            const boxes = document.querySelectorAll('#previewStage .prev-box');
            const r = {};
            boxes.forEach((b, i) => { r['box'+i] = getComputedStyle(b).backgroundColor; });
            const stage = document.getElementById('previewStage');
            r['_stage'] = stage ? getComputedStyle(stage).backgroundColor : null;
            return r;
        })()
    ''')
    print('  Dark mode boxes:')
    for k, v in dark_boxes.items(): print(f'    {k}: {v}')

    # Toggle light
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    light_boxes = page.evaluate('''
        (() => {
            const boxes = document.querySelectorAll('#previewStage .prev-box');
            const r = {};
            boxes.forEach((b, i) => { r['box'+i] = getComputedStyle(b).backgroundColor; });
            const stage = document.getElementById('previewStage');
            r['_stage'] = stage ? getComputedStyle(stage).backgroundColor : null;
            return r;
        })()
    ''')
    print('  Light mode boxes:')
    for k, v in light_boxes.items(): print(f'    {k}: {v}')

    # Check if light boxes are lighter than dark boxes
    for k in list(light_boxes.keys())[:3]:
        lv = light_boxes[k]
        dv = dark_boxes.get(k, '')
        print(f'  {k} light={lv} vs dark={dv}')

    # Slider bg
    slider_bg = page.evaluate('getComputedStyle(document.getElementById("rangeTransparency")).backgroundColor')
    print(f'  Slider track bg (light): {slider_bg}')

    # ====== Test 2: Front repo - Blog click, screen folder, image picker border ======
    print('\n=== [2] Front repo - blog, screen folder, image picker border ===')
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)

    # Open sua package
    for b in page.query_selector_all('button'):
        if b.text_content().strip() == 'Sửa':
            b.click(); break
    page.wait_for_timeout(1000)

    # Check screen folder/search bg in dark
    dark_screen = page.evaluate('''
        (() => {
            const r = {};
            const ids = ['f_screen_folder', 'f_screen_search', 'f_icon_folder', 'f_icon_search'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) r[id] = getComputedStyle(el).backgroundColor;
            }
            return r;
        })()
    ''')
    print('  Dark mode screen/icon folder/search:')
    for k, v in dark_screen.items(): print(f'    {k}: {v}')

    # Toggle light
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    light_screen = page.evaluate('''
        (() => {
            const r = {};
            const ids = ['f_screen_folder', 'f_screen_search', 'f_icon_folder', 'f_icon_search'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) r[id] = getComputedStyle(el).backgroundColor;
            }
            return r;
        })()
    ''')
    print('  Light mode screen/icon folder/search:')
    for k, v in light_screen.items(): print(f'    {k}: {v}')

    # Test image picker border (open screen grid)
    page.evaluate('''
        (() => {
            // Open screen grid by clicking refresh
            const refreshBtn = document.getElementById('btnRefreshFolders');
            if (refreshBtn) refreshBtn.click();
        })()
    ''')
    page.wait_for_timeout(1500)
    page.evaluate('''
        (() => {
            // Trigger grid refresh manually
            const event = new Event('input', {bubbles:true});
            const searchEl = document.getElementById('f_screen_search');
            if (searchEl) { searchEl.value = ''; searchEl.dispatchEvent(event); }
        })()
    ''')
    page.wait_for_timeout(1500)

    # Click on first screen image to select it
    clicked = page.evaluate('''
        (() => {
            const grid = document.getElementById('screensGrid');
            if (!grid) return 'no_grid';
            const items = grid.querySelectorAll('[data-path]');
            if (items.length === 0) return 'no_items';
            // Click first item
            items[0].click();
            return items.length + '_items';
        })()
    ''')
    print(f'  Screen grid items clicked: {clicked}')
    page.wait_for_timeout(500)

    selected_border = page.evaluate('''
        (() => {
            const grid = document.getElementById('screensGrid');
            if (!grid) return null;
            const items = grid.querySelectorAll('[data-path]');
            for (const item of items) {
                const cls = item.className;
                const bColor = getComputedStyle(item).borderTopColor;
                const boxShadow = getComputedStyle(item).boxShadow;
                const isSelected = cls.includes('border-green-500');
                if (isSelected) {
                    return { borderColor: bColor, boxShadow: boxShadow.substring(0, 60) };
                }
            }
            return null;
        })()
    ''')
    print(f'  Selected image border/shadow: {selected_border}')

    # Check slider bg
    slider_bg_front = page.evaluate('getComputedStyle(document.getElementById("rangeTransparency")).backgroundColor')
    print(f'  Front slider track bg (light): {slider_bg_front}')

    # Screenshot
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix12_dash_light.png')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix12_front_light.png')

    browser.close()
    print('\n=== DONE ===')
