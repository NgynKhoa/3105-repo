# -*- coding: utf-8 -*-
"""Test save button - wait for full process"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import subprocess, json

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()
    page = ctx.new_page()
    page.set_viewport_size({'width': 1400, 'height': 1000})

    # Capture network
    api_calls = []
    page.on('request', lambda r: api_calls.append(f'{r.method} {r.url}') if '/api/' in r.url else None)
    page.on('response', lambda r: api_calls.append(f'  -> {r.status} {r.url}') if '/api/' in r.url else None)

    errors = []
    page.on('pageerror', lambda e: errors.append('PAGE:' + str(e)))
    page.on('console', lambda m: errors.append(f'CONSOLE[{m.type}]:{m.text}') if m.type == 'error' else None)

    page.goto(BASE + '/?_=t1')
    page.wait_for_timeout(3000)

    # First modify a package by edit+save in JS (no need to actually edit)
    # Just click btnSave directly - it should call save + push
    api_calls.clear()
    page.evaluate('document.getElementById("btnSave").click()')
    print('Clicked btnSave. Waiting for response...')

    # Poll toast for 20 seconds
    for i in range(40):
        page.wait_for_timeout(500)
        toast = page.evaluate('''
            (() => {
                const t = document.getElementById('toast');
                if (!t) return 'NO toast element';
                return t.textContent + ' [class=' + t.className + ']';
            })()
        ''')
        if 'Push' in toast or 'Lỗi' in toast or '✓' in toast or 'commit' in toast.lower():
            print(f'  Toast at t={i*0.5}s: {toast!r}')
            break
        if i % 10 == 9:
            print(f'  t={i*0.5}s: {toast!r}')
    else:
        print(f'Final toast: {toast!r}')

    # Final api calls
    print('\nAPI calls:')
    for c in api_calls[:30]:
        print(f'  {c}')

    print('\nErrors:', errors[:5])

    # Check git status
    r = subprocess.run(['git', '-C', r'c:\Users\NK\Desktop\MOD\3105-repo', 'log', '--oneline', '-5'], capture_output=True, text=True)
    print('\nLast 5 commits:')
    print(r.stdout)

    browser.close()
