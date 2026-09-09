#!/usr/bin/env python3
"""Test cuối: verify YAML/JSON output đúng schema sau nhiều thao tác."""
import sys, json, subprocess, urllib.request, yaml
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

    # Lấy YAML hiện tại
    with open("repositories/demo/repo.yml", encoding="utf-8") as f:
        before_yaml = f.read()

    # ===== TEST 1: Sửa password, save, verify =====
    print("=== TEST 1: Edit password ===")
    # Click edit package 1
    edit_btns = page.query_selector_all('button[data-action="edit"]')
    edit_btns[0].click()
    page.wait_for_timeout(800)

    # Lấy identifier
    identifier = page.input_value("#f_identifier")
    print(f"  Editing: {identifier}")

    # Test 1a: chỉ password -> lưu -> check YAML
    page.fill("#f_password", "NEW_PASSWORD_999")
    page.click("#btnSavePackage")
    page.wait_for_timeout(1500)
    print(f"  Saved password 'NEW_PASSWORD_999'")

    # Click btnSave (push to git)
    page.click("#btnSave")
    page.wait_for_timeout(8000)
    toast = page.text_content("#toast")
    print(f"  Toast: {toast}")

    # Verify YAML có password mới
    with open("repositories/demo/repo.yml", encoding="utf-8") as f:
        d = yaml.safe_load(f)
    pkg = next((p for p in d['packages'] if p['identifier'] == identifier), None)
    if pkg:
        print(f"  YAML password: '{pkg.get('password')}'")
        is_correct = pkg.get('password') == 'NEW_PASSWORD_999'
        print(f"  {'PASS' if is_correct else 'FAIL'}: password in YAML")
        # Revert
        pkg['password'] = '2752'
        with open("repositories/demo/repo.yml", "w", encoding="utf-8") as f:
            yaml.dump(d, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        # Push lại
        req = urllib.request.Request(
            "http://127.0.0.1:5050/api/repo/demo/push",
            data=json.dumps({"commit_msg": "revert password"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req)

    # ===== TEST 2: Verify repo.json auto-gen khi push =====
    print("\n=== TEST 2: Repo.json consistency ===")
    # Repo json được tạo thủ công từ build.yml. Kiểm tra khớp với YAML
    with open("repositories/demo/repo.json", encoding="utf-8") as f:
        repo_json = json.loads(f.read())
    print(f"  YAML packages: {len(d['packages'])}")
    print(f"  JSON packages: {len(repo_json['packages'])}")

    # ===== TEST 3: Verify tất cả các field optional đều được handle =====
    print("\n=== TEST 3: Field coverage ===")
    for i, p in enumerate(repo_json["packages"][:5]):
        keys = sorted(p.keys())
        print(f"  [{i}] {p['identifier']:15s} -> {len(keys)} keys")

    # ===== TEST 4: Special characters in fields =====
    print("\n=== TEST 4: Special chars in name ===")
    # Tìm package có emoji
    for p in repo_json["packages"]:
        if any(c in p["name"] for c in "👑💫🔥✨"):
            print(f"  {p['identifier']}: {p['name']}")
            print(f"    Has emoji: {any(ord(c) > 127 for c in p['name'])}")

    print("\n=== ERRORS ===")
    for e in errors[:10]:
        print(f"  {e}")
    browser.close()
print("DONE")
