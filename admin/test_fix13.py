# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    page.goto(f'{BASE}/dashboard?_=d1')
    page.wait_for_timeout(2500)
    page.evaluate('localStorage.clear()')
    page.goto(f'{BASE}/dashboard?_=d2')
    page.wait_for_timeout(2500)

    # Check theme grid in dashboard settings menu
    page.click('#settingsBtn' if page.locator('#settingsBtn').count() else '#btnOpenSettings')
    page.wait_for_timeout(500)

    dash_theme = page.evaluate('''
        (() => {
            const grid = document.getElementById('themeGrid');
            if (!grid) return 'no_grid';
            const gridStyle = getComputedStyle(grid);
            const btns = grid.querySelectorAll('.theme-btn');
            const r = {
                '_grid_display': gridStyle.display,
                '_grid_cols': gridStyle.gridTemplateColumns,
                '_grid_width': grid.offsetWidth,
                '_btn_count': btns.length,
            };
            if (btns.length > 0) {
                const first = btns[0];
                const rect = first.getBoundingClientRect();
                const style = getComputedStyle(first);
                r['_btn0_width'] = rect.width;
                r['_btn0_height'] = rect.height;
                r['_btn0_bg'] = style.backgroundImage.substring(0, 60);
                r['_btn0_border'] = style.borderTopColor;
            }
            return r;
        })()
    ''')
    print('=== Dashboard settings theme grid ===')
    if isinstance(dash_theme, dict):
        for k, v in dash_theme.items(): print(f'  {k}: {v}')
    else:
        print(f'  {dash_theme}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix13_dash_settings.png')

    # Close dashboard, test front repo
    page.goto(BASE + '?_=f1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=f2')
    page.wait_for_timeout(2500)

    page.click('#settingsBtn')
    page.wait_for_timeout(500)

    front_theme = page.evaluate('''
        (() => {
            const grid = document.getElementById('themeGrid');
            if (!grid) return 'no_grid';
            const gridStyle = getComputedStyle(grid);
            const btns = grid.querySelectorAll('.theme-btn');
            const r = {
                '_grid_display': gridStyle.display,
                '_grid_cols': gridStyle.gridTemplateColumns,
                '_grid_width': grid.offsetWidth,
                '_btn_count': btns.length,
            };
            if (btns.length > 0) {
                const first = btns[0];
                const rect = first.getBoundingClientRect();
                const style = getComputedStyle(first);
                r['_btn0_width'] = rect.width;
                r['_btn0_height'] = rect.height;
                r['_btn0_bg'] = style.backgroundImage.substring(0, 60);
                r['_btn0_border'] = style.borderTopColor;

                const last = btns[btns.length - 1];
                r['_btn_last_width'] = last.getBoundingClientRect().width;
                r['_btn_last_height'] = last.getBoundingClientRect().height;
            }
            // Check parent of grid
            const parent = grid.parentElement;
            r['_parent_width'] = parent.offsetWidth;
            r['_parent_class'] = parent.className;

            // Settings menu width
            const menu = document.getElementById('settingsMenu');
            if (menu) {
                const menuStyle = getComputedStyle(menu);
                r['_menu_width'] = menu.offsetWidth;
                r['_menu_max_width'] = menuStyle.maxWidth;
            }
            return r;
        })()
    ''')
    print('\n=== Front repo settings theme grid ===')
    if isinstance(front_theme, dict):
        for k, v in front_theme.items(): print(f'  {k}: {v}')
    else:
        print(f'  {front_theme}')
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix13_front_settings.png')

    browser.close()
    print('\n=== DONE ===')
