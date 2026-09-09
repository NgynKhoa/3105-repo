#!/usr/bin/env python3
"""Test repo.json được sinh đúng schema, edge cases như tags, password, dates."""
import sys, json, subprocess, urllib.request
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

    # Edge case 1: Click edit package đầu tiên, kiểm tra dates
    print("=== EDGE CASE 1: Edit package có dates ===")
    edit_btns = page.query_selector_all('button[data-action="edit"]')
    if edit_btns:
        edit_btns[0].click()
        page.wait_for_timeout(800)

        # Check if "Không dùng publishedAt" checkbox
        no_pub = page.query_selector("#f_no_publishedAt")
        if no_pub:
            is_checked = page.is_checked("#f_no_publishedAt")
            print(f"  f_no_publishedAt checked: {is_checked}")

        # If publishedAt exists, test "Bây giờ" button
        now_btn = page.query_selector("#btnNowPublishedAt")
        if now_btn and now_btn.is_visible():
            page.click("#btnNowPublishedAt")
            page.wait_for_timeout(300)
            pub_val = page.input_value("#f_publishedAt")
            print(f"  PublishedAt after 'Now': {pub_val}")
            check_valid = bool(pub_val and len(pub_val) >= 16)
            print(f"  Valid datetime: {check_valid}")

        page.click("#btnCloseModal")
        page.wait_for_timeout(500)

    # Edge case 2: Edit package có tags - thêm tag mới
    print("\n=== EDGE CASE 2: Tags ===")
    edit_btns = page.query_selector_all('button[data-action="edit"]')
    # Tìm package có tags
    for btn in edit_btns:
        btn.click()
        page.wait_for_timeout(500)
        tags_val = page.input_value("#f_tags")
        if tags_val and "Dialer" in tags_val:
            print(f"  Tags: '{tags_val}'")
            # Thêm tag mới
            page.fill("#f_tags", tags_val + ", EXTRA_TAG")
            page.click("#btnSavePackage")
            page.wait_for_timeout(1500)
            toast = page.text_content("#toast")
            print(f"  Toast: '{toast}'")
            # Verify qua API
            req = urllib.request.urlopen("http://127.0.0.1:5050/api/repo/demo/packages").read()
            data = json.loads(req)
            for p in data["packages"]:
                if p.get("tags") and "EXTRA_TAG" in p.get("tags", []):
                    print(f"  Tag saved in: {p['identifier']}")
                    break
            # Revert
            page.fill("#f_tags", tags_val)
            page.click("#btnSavePackage")
            page.wait_for_timeout(1000)
            break
        page.click("#btnCloseModal")
        page.wait_for_timeout(300)

    # Edge case 3: Kiểm tra repo.json được gen đúng schema
    print("\n=== EDGE CASE 3: repo.json schema ===")
    with open("repositories/demo/repo.json", encoding="utf-8") as f:
        repo_json = json.loads(f.read())

    print(f"  Total packages: {len(repo_json['packages'])}")
    print(f"  Repo identifier: {repo_json.get('identifier')}")
    print(f"  Repo name: {repo_json.get('name')}")
    print(f"  Schema version: {repo_json.get('schemaVersion')}")

    # Check từng package có đủ field bắt buộc
    required = ["identifier", "name", "version", "sha256", "size", "download",
                "icon", "screenshots", "supportedOS", "description", "changelog"]
    missing = []
    for i, p in enumerate(repo_json["packages"]):
        for fld in required:
            if fld not in p:
                missing.append(f"{p.get('identifier', i)}.{fld}")
    print(f"  Missing fields: {len(missing)}")
    if missing:
        for m in missing[:5]:
            print(f"    - {m}")

    # Verify supportedOS schema
    bad_os = []
    for p in repo_json["packages"]:
        for rule in p.get("supportedOS", []):
            if "minimum" not in rule or "maximum" not in rule:
                bad_os.append(p["identifier"])
    print(f"  Packages with bad OS rules: {len(bad_os)}")
    if bad_os:
        print(f"    {bad_os}")

    # Verify size là số
    bad_size = [p["identifier"] for p in repo_json["packages"] if not isinstance(p.get("size"), int)]
    print(f"  Packages with non-int size: {len(bad_size)}")

    # Verify sha256 là hex 64
    import re
    bad_sha = [p["identifier"] for p in repo_json["packages"]
                if not re.match(r"^[0-9A-F]{64}$", p.get("sha256", ""))]
    print(f"  Packages with bad sha256: {len(bad_sha)}")

    # Edge case 4: Empty repo (just for fun, skip)
    print("\n=== EDGE CASE 4: File .3105 combobox - click chọn ===")
    page.click("#btnAdd")
    page.wait_for_timeout(800)
    page.focus("#f_download")
    page.wait_for_timeout(300)
    items = page.eval_on_selector_all("#f_download_menu .dl-item", "els => els.map(e => e.dataset.val)")
    print(f"  Initial items: {len(items)}")
    # Click item có .3105pass (test cả 2 ext)
    pass_items = [i for i in items if ".3105pass" in i]
    print(f"  .3105pass files: {len(pass_items)}")
    if pass_items:
        page.click(f"#f_download_menu .dl-item >> nth={items.index(pass_items[0])}")
        page.wait_for_timeout(300)
        val = page.input_value("#f_download")
        print(f"  Selected: '{val}'")
        # Click ⚡ Lấy hash
        page.click("#btnAutoFill")
        page.wait_for_timeout(800)
        sha = page.input_value("#f_sha256")
        size = page.input_value("#f_size")
        print(f"  SHA256 (len={len(sha)}): {sha[:16]}...")
        print(f"  Size: {size}")

    # Test clear button (X)
    print("\n=== EDGE CASE 5: Clear download ===")
    clear_visible = page.is_visible("#f_download_clear")
    print(f"  Clear btn visible: {clear_visible}")
    if clear_visible:
        page.click("#f_download_clear")
        page.wait_for_timeout(300)
        val = page.input_value("#f_download")
        print(f"  After clear: '{val}'")

    page.click("#btnCloseModal")
    page.wait_for_timeout(500)

    print("\n=== ERRORS ===")
    for e in errors[:10]:
        print(f"  {e}")
    browser.close()
print("DONE")
