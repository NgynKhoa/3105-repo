#!/usr/bin/env python3
"""Test push git end-to-end: thêm package, lưu + push, verify file trên đĩa."""
import sys, json, subprocess, urllib.request, time
sys.stdout.reconfigure(encoding="utf-8")
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = ctx.new_page()
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"PAGE: {e}"))

    page.goto("http://127.0.0.1:5050/", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    # Lấy số package trước
    with open("repositories/demo/repo.yml", encoding="utf-8") as f:
        before = f.read()
    before_count = before.count("\n  - identifier:")
    print(f"=== BEFORE: {before_count} packages ===")

    # Mở modal thêm
    page.click("#btnAdd")
    page.wait_for_timeout(800)

    # Auto-fill hash
    page.focus("#f_download")
    page.wait_for_timeout(300)
    items = page.eval_on_selector_all("#f_download_menu .dl-item", "els => els.map(e => e.dataset.val)")
    if items:
        page.click("#f_download_menu .dl-item >> nth=0")
        page.wait_for_timeout(200)
        page.click("#btnAutoFill")
        page.wait_for_timeout(800)

    page.fill("#f_name", "Test Package EndToEnd")
    page.fill("#f_summary", "Test thêm package end-to-end")
    page.fill("#f_password", "testpass")
    page.fill("#f_description", "Mô tả test\nNhiều dòng")
    page.fill("#f_changelog", "v1.0.0 - Test changelog")

    # Lưu package (chưa push)
    page.click("#btnSavePackage")
    page.wait_for_timeout(1500)
    toast = page.text_content("#toast")
    print(f"After save package: '{toast}'")

    # Click Lưu & Push Git
    page.click("#btnSave")
    page.wait_for_timeout(500)
    box = page.eval_on_selector("#btnSave", "el => ({w: el.offsetWidth, h: el.offsetHeight, disabled: el.disabled})")
    print(f"Save button during push: {box}")

    # Đợi push xong (3-5s)
    page.wait_for_timeout(8000)
    toast = page.text_content("#toast")
    print(f"After push: '{toast}'")

    # Verify repo.yml đã cập nhật
    with open("repositories/demo/repo.yml", encoding="utf-8") as f:
        after = f.read()
    after_count = after.count("\n  - identifier:")
    print(f"=== AFTER: {after_count} packages ===")
    has_new_pkg = "Test Package EndToEnd" in after
    print(f"  Contains 'Test Package EndToEnd': {has_new_pkg}")

    # Verify git status
    result = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True, encoding="utf-8", cwd=".")
    print(f"Git log:\n{result.stdout}")

    # Reset: xóa package vừa thêm
    print("\n=== CLEANUP ===")
    # Click edit package vừa thêm (tìm theo identifier)
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(2000)
    # Tìm trong list
    items = page.eval_on_selector_all(".pkg-item", "els => els.length")
    print(f"  Items in list after reload: {items}")

    # Lấy identifier mới
    import yaml
    with open("repositories/demo/repo.yml", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    if d['packages']:
        last = d['packages'][-1]
        print(f"  Last package: {last['identifier']} - {last['name']}")
        if 'EndToEnd' in last.get('name', ''):
            # Xóa
            print("  Need to remove test package")
            payload = {
                "repoMeta": {k: d.get(k) for k in ["schemaVersion", "identifier", "name", "description", "icon", "accentColor"]},
                "packages": d['packages'][:-1],
                "packagesMeta": [{"use_anchor_os": True, "use_anchor_screens": True}] * (len(d['packages']) - 1),
            }
            req = urllib.request.Request(
                "http://127.0.0.1:5050/api/repo/demo/save",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req)
            print("  Saved without test package")

            # Push
            req = urllib.request.Request(
                "http://127.0.0.1:5050/api/repo/demo/push",
                data=json.dumps({"commit_msg": "Remove test package"}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req)
            print(f"  Push result: {resp.read().decode('utf-8')[:200]}")

    # Verify đã revert
    with open("repositories/demo/repo.yml", encoding="utf-8") as f:
        final = f.read()
    final_count = final.count("\n  - identifier:")
    print(f"=== FINAL: {final_count} packages ===")

    print("\n=== ERRORS ===")
    for e in errors[:10]:
        print(f"  {e}")
    browser.close()
print("DONE")
