# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 1400, 'height': 900})

    page.goto(BASE + '?_=t1')
    page.wait_for_timeout(2000)
    page.evaluate('localStorage.clear()')
    page.goto(BASE + '?_=t2')
    page.wait_for_timeout(2500)

    # Open sua package first
    for b in page.query_selector_all('button'):
        if b.text_content().strip() == 'Sửa':
            b.click(); break
    page.wait_for_timeout(1000)

    # Toggle light
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    light = page.evaluate('''
        (() => {
            const r = {};
            const ids = ['f_icon_folder', 'f_icon_search', 'f_banner_folder', 'f_banner_search'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) r[id] = getComputedStyle(el).backgroundColor;
            }
            const btn = document.querySelector('.neon-delete');
            if (btn) r['_btn_delete_border'] = getComputedStyle(btn).borderColor;
            const btnEdit = document.querySelector('.neon-edit');
            if (btnEdit) r['_btn_edit_border'] = getComputedStyle(btnEdit).borderColor;
            const trash = document.querySelector('#btnDeleteIconFolder svg');
            r['_trash_has_svg'] = !!trash;
            return r;
        })()
    ''')
    print('=== Light mode ===')
    for k, v in light.items(): print(f'  {k}: {v}')

    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/fix11_light.png')

    # Toggle back dark
    page.click('#settingsBtn')
    page.wait_for_timeout(300)
    page.evaluate('document.getElementById("toggleDarkMode").click()')
    page.wait_for_timeout(500)
    page.click('#closeSettings')
    page.wait_for_timeout(300)

    back = page.evaluate('''
        (() => {
            const r = {};
            const ids = ['f_icon_folder', 'f_icon_search', 'f_banner_folder', 'f_banner_search'];
            for (const id of ids) {
                const el = document.getElementById(id);
                if (el) r[id] = getComputedStyle(el).backgroundColor;
            }
            return r;
        })()
    ''')
    print('=== Back to Dark ===')
    for k, v in back.items(): print(f'  {k}: {v}')

    browser.close()
    print('=== DONE ===')
