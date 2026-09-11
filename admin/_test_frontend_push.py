# -*- coding: utf-8 -*-
"""Reproduce click on btnSave via Playwright"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_viewport_size({'width': 1400, 'height': 1000})
    errors = []
    page.on('pageerror', lambda e: errors.append('PAGE:' + str(e)))
    page.on('console', lambda m: errors.append(f'CONSOLE[{m.type}]:{m.text}') if m.type == 'error' else None)

    page.goto(BASE + '/?_=t1')
    page.wait_for_timeout(3000)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/t_front1.png', full_page=True)

    # Find the save button
    btns = page.evaluate('''
        Array.from(document.querySelectorAll("button")).map(b => ({
            id: b.id,
            text: (b.textContent || '').trim().slice(0,30),
            visible: b.offsetParent !== null
        })).filter(b => b.id || b.text)
    ''')
    print('Buttons:')
    for b in btns:
        bid = b.get('id') or ''
        bt = b.get('text') or ''
        print(f'  id={bid!s:20}  text={bt!s:30}  vis={b.get("visible")}')

    # Click save
    save_clicked = page.evaluate('''
        (() => {
            const btn = document.getElementById('btnSave');
            if (!btn) return 'btnSave NOT FOUND';
            btn.click();
            return 'CLICKED';
        })()
    ''')
    print('Save click:', save_clicked)
    page.wait_for_timeout(8000)
    page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/t_front2.png', full_page=True)

    # Toast content
    toast = page.evaluate('''
        (() => {
            const t = document.getElementById('toast');
            return t ? t.textContent : 'no toast element';
        })()
    ''')
    print('Toast:', toast)

    print('Errors:', errors[:5])
    browser.close()
