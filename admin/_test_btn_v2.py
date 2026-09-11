# -*- coding: utf-8 -*-
"""Verify push button shows progress modal and works"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_viewport_size({'width': 1400, 'height': 1000})
    page.on('dialog', lambda d: d.accept())

    api_calls = []
    errors = []
    page.on('request', lambda r: api_calls.append(f'>> {r.method} {r.url}') if '/api/' in r.url else None)
    page.on('response', lambda r: api_calls.append(f'<< {r.status} {r.url[-80:]}') if '/api/' in r.url else None)
    page.on('pageerror', lambda e: errors.append('PAGE:' + str(e)))
    page.on('console', lambda m: errors.append(f'CONSOLE[{m.type}]:{m.text}') if m.type == 'error' else None)

    page.goto(BASE + '/?_=t99')
    page.wait_for_timeout(5000)

    info = page.evaluate('({ pkgs: state?.packages?.length, repo: state?.currentRepo })')
    print('State:', info)

    api_calls.clear()
    print('\n>>> Clicking btnSave...')
    page.evaluate('document.getElementById("btnSave").click()')
    page.wait_for_timeout(3000)

    # Modal should be visible
    modal_exists = page.evaluate('document.getElementById("pushProgressModal") !== null')
    print('Modal exists after 3s:', modal_exists)

    if modal_exists:
        page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/t_push_progress.png', full_page=True)

        # Get step statuses
        steps = page.evaluate('''
            (() => {
                return ['save','pull','add','status','commit','push'].map(id => {
                    const icon = document.getElementById('step-' + id + '-icon');
                    const detail = document.getElementById('step-' + id + '-detail');
                    return { id, icon: icon?.textContent, hasDetail: detail?.style?.display !== 'none' };
                });
            })()
        ''')
        print('Steps:')
        for s in steps:
            print(f"  {s['id']:8} {s['icon']:6} hasDetail={s['hasDetail']}")

    page.wait_for_timeout(15000)
    if modal_exists:
        page.screenshot(path='c:/Users/NK/Desktop/MOD/3105-repo/admin/t_push_progress2.png', full_page=True)

    toast = page.evaluate('document.getElementById("toast")?.textContent || ""')
    print(f'\nFinal toast: {toast!r}')

    print('\nAPI calls:')
    for c in api_calls[:30]:
        print(f'  {c}')

    print(f'\nErrors: {errors[:3]}')
    browser.close()
