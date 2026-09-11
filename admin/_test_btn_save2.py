# -*- coding: utf-8 -*-
"""Test btnSave with confirm dialogs auto-accepted"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright
import subprocess

BASE = 'http://127.0.0.1:5050'

with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context()
    # Auto-accept all dialogs (including prompt + confirm)
    page = ctx.new_page()
    page.on('dialog', lambda d: (print(f'DIALOG [{d.type}]: {d.message!r:.60}'), d.accept()))

    api_calls = []
    page.on('request', lambda r: api_calls.append(f'>> {r.method} {r.url}') if '/api/' in r.url else None)
    page.on('response', lambda r: api_calls.append(f'<< {r.status} {r.url}') if '/api/' in r.url else None)

    errors = []
    page.on('pageerror', lambda e: errors.append('PAGE:' + str(e)))
    page.on('console', lambda m: errors.append(f'CONSOLE[{m.type}]:{m.text}') if m.type == 'error' else None)

    page.goto(BASE + '/?_=t1')
    page.wait_for_timeout(4000)

    # Get package count and changes
    info = page.evaluate('({ pkgs: state.packages.length, changes: state.changes, repo: state.currentRepo })')
    print('State:', info)

    api_calls.clear()
    print('Clicking btnSave...')
    page.evaluate('document.getElementById("btnSave").click()')
    page.wait_for_timeout(20000)  # wait for push

    print('API calls during save:')
    for c in api_calls[:30]:
        print(f'  {c}')

    toast = page.evaluate('document.getElementById("toast")?.textContent || ""')
    print(f'Final toast: {toast!r}')

    print(f'Errors: {errors[:3]}')

    browser.close()
