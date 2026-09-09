#!/usr/bin/env python3
"""Playwright test - Khởi động browser, test trang chính."""
import sys, json, time
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

console_msgs = []
page_errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text}"))
    page.on("pageerror", lambda err: page_errors.append(str(err)))

    print("=== LOAD http://127.0.0.1:5050/ ===")
    page.goto("http://127.0.0.1:5050/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    title = page.title()
    print(f"Title: {title}")

    # Kiểm tra các element quan trọng
    checks = {
        "shell": "#shell",
        "masthead": "#masthead",
        "logo": "#logo",
        "repoSelect": "#repoSelect",
        "packageList": "#packageList",
        "addPkgBtn": "#btnAddPackage",
        "saveBtn": "#btnSave",
        "pushBtn": "#btnPush",
        "meta_identifier": "#meta_identifier",
        "meta_name": "#meta_name",
        "pkgSearchInput": "#pkgSearchInput",
        "modal": "#modal",
        "toast": "#toast",
    }
    print("\n=== ELEMENT CHECK ===")
    for name, sel in checks.items():
        try:
            el = page.query_selector(sel)
            visible = el.is_visible() if el else False
            print(f"  {name:20s} ({sel:25s}) -> {'OK' if el else 'MISSING'} visible={visible}")
        except Exception as e:
            print(f"  {name:20s} ({sel:25s}) -> ERROR: {e}")

    # Lấy thông tin repo dropdown
    print("\n=== REPO DROPDOWN ===")
    opts = page.eval_on_selector_all("#repoSelect option", "els => els.map(o => ({value:o.value, text:o.textContent}))")
    for o in opts:
        print(f"  '{o['value']}' -> '{o['text']}'")

    # Lấy thông tin package list
    print("\n=== PACKAGE LIST ===")
    pkgs = page.eval_on_selector_all(".pkg-item", "els => els.length")
    print(f"Total visible packages: {pkgs}")

    # Chờ 2s để load xong
    page.wait_for_timeout(2000)
    pkgs_after = page.eval_on_selector_all(".pkg-item", "els => els.length")
    print(f"After 2s: {pkgs_after}")

    # Kiểm tra masthead avatar
    print("\n=== MASTHEAD ===")
    avatar_html = page.eval_on_selector("#mast-avatar", "el => el.innerHTML.slice(0, 200)")
    print(f"Avatar HTML (200 chars): {avatar_html[:200]}")

    # Thử mở modal
    print("\n=== OPEN MODAL ===")
    try:
        page.click("#btnAddPackage", timeout=5000)
        page.wait_for_timeout(800)
        modal_visible = page.is_visible("#modal")
        print(f"Modal visible after click: {modal_visible}")
        if modal_visible:
            # Đếm input trong form
            inputs = page.eval_on_selector_all("#modalBody input, #modalBody select, #modalBody textarea", "els => els.length")
            print(f"Inputs in modal: {inputs}")
            page.click("#modalClose", timeout=3000)
    except Exception as e:
        print(f"Modal error: {e}")

    print("\n=== CONSOLE MESSAGES ===")
    for m in console_msgs[-20:]:
        print(f"  {m}")

    print("\n=== PAGE ERRORS ===")
    for e in page_errors:
        print(f"  {e}")

    browser.close()
print("\n=== DONE ===")
