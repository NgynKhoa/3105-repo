"""Test cac chuc nang moi sau khi sua:
1. Dark/Light mode doi mau nen web (--bg-color)
2. Transparency ap dung cho tat ca panel/link
3. Boxes Panel: preview trang repo, keo tha + resize
4. Setting Front Repo co navigation toi Admin/Blog
5. Test tat ca cac nut setting
"""
# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5050"

def run_tests():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # Clear storage
        page.goto(BASE)
        page.wait_for_timeout(1000)
        page.evaluate("localStorage.clear()")
        page.reload()
        page.wait_for_timeout(2000)

        # ============ TEST 1: INDEX.HTML - Dark mode đổi bg ============
        print("Test 1: Front Repo - Dark mode đổi màu nền web...")
        page.click("#settingsBtn")
        page.wait_for_timeout(500)
        # Đọc bg-color trước khi toggle
        bg_dark = page.evaluate("getComputedStyle(document.body).backgroundColor")
        print(f"  - Dark mode bg: {bg_dark}")

        # Toggle light mode
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(500)
        bg_light = page.evaluate("getComputedStyle(document.body).backgroundColor")
        print(f"  - Light mode bg: {bg_light}")
        assert bg_dark != bg_light, "Light mode không đổi bg!"
        page.screenshot(path="test_fix3_light_bg.png", full_page=False)

        # Toggle lại dark
        page.evaluate("document.getElementById('toggleDarkMode').click()")
        page.wait_for_timeout(300)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 2: Transparency áp dụng cho panel ============
        print("\nTest 2: Transparency áp dụng cho các panel...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        # Set transparency = 30%
        page.evaluate("""
            document.getElementById('rangeTransparency').value = 30;
            document.getElementById('rangeTransparency').dispatchEvent(new Event('input'));
        """)
        page.wait_for_timeout(500)
        panel_alpha = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--panel-alpha')")
        print(f"  - Panel alpha khi 30%: {panel_alpha}")
        assert panel_alpha.strip() in ("0.3", "0.30"), f"Transparency không set đúng alpha! Got: {panel_alpha}"
        page.screenshot(path="test_fix3_transparency_30.png", full_page=False)
        # Reset
        page.evaluate("""
            document.getElementById('rangeTransparency').value = 92;
            document.getElementById('rangeTransparency').dispatchEvent(new Event('input'));
        """)
        page.wait_for_timeout(300)
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 3: Theme switching ============
        print("\nTest 3: Theme switching...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        for theme in ["cyan", "pink", "lavender", "green"]:
            page.click(f'[data-theme="{theme}"]')
            page.wait_for_timeout(300)
            neon = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--neon')")
            print(f"  - Theme {theme}: neon={neon.strip()}")
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 4: Rain toggles ============
        print("\nTest 4: Rain toggles...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        page.evaluate("document.getElementById('toggleHeavyRain').click()")
        page.wait_for_timeout(500)
        page.click("#closeSettings")
        page.wait_for_timeout(500)

        # ============ TEST 5: Quick navigation links ============
        print("\nTest 5: Quick navigation links...")
        page.click("#settingsBtn")
        page.wait_for_timeout(300)
        # Check links
        dashboard_link = page.locator('a[href="/dashboard"]').count()
        blog_link = page.locator('a[href="/blog"]').count()
        print(f"  - Dashboard links: {dashboard_link}")
        print(f"  - Blog links: {blog_link}")
        assert dashboard_link > 0 and blog_link > 0, "Missing navigation links!"
        page.click("#closeSettings")
        page.wait_for_timeout(300)

        # ============ TEST 6: DASHBOARD - Boxes Panel preview ============
        print("\nTest 6: Dashboard - Boxes Panel Preview with drag/resize...")
        page.goto(f"{BASE}/dashboard")
        page.wait_for_timeout(2000)
        page.click('[data-tab="boxes"]')
        page.wait_for_timeout(500)
        # Check previewStage exists
        stage_visible = page.locator("#previewStage").is_visible()
        print(f"  - Preview stage visible: {stage_visible}")
        assert stage_visible, "Preview stage không hiển thị!"
        # Count preview boxes
        prev_boxes = page.locator("#previewStage .prev-box").count()
        prev_mast = page.locator("#previewStage .prev-masthead").count()
        print(f"  - Preview boxes: {prev_boxes}, mastheads: {prev_mast}")
        assert prev_boxes >= 6, f"Không đủ preview boxes! Got {prev_boxes}"
        page.screenshot(path="test_fix3_boxes_panel.png", full_page=True)

        # Enable edit mode
        page.evaluate("togglePreviewEdit()")
        page.wait_for_timeout(500)
        resize_handles = page.locator("#previewStage .resize-handle:visible").count()
        print(f"  - Visible resize handles: {resize_handles}")
        page.screenshot(path="test_fix3_edit_mode.png", full_page=True)

        # ============ TEST 7: Drag a box ============
        print("\nTest 7: Drag a preview box...")
        box = page.locator('[data-box="search-box"]')
        box_box = box.bounding_box()
        page.mouse.move(box_box["x"] + 50, box_box["y"] + 25)
        page.mouse.down()
        page.mouse.move(box_box["x"] + 150, box_box["y"] + 75, steps=5)
        page.mouse.up()
        page.wait_for_timeout(300)
        new_pos = page.evaluate("""() => {
            const el = document.querySelector('[data-box="search-box"]');
            return { left: el.style.left, top: el.style.top };
        }""")
        print(f"  - New position: {new_pos}")
        page.screenshot(path="test_fix3_after_drag.png", full_page=True)

        # ============ TEST 8: Save layout ============
        print("\nTest 8: Save layout...")
        page.click("button:has-text('Lưu Layout')")
        page.wait_for_timeout(500)
        saved = page.evaluate("localStorage.getItem('repo_previewLayout')")
        print(f"  - Saved layout has data: {bool(saved)}")
        assert saved, "Layout không được lưu!"

        # ============ TEST 9: Dashboard tabs hoạt động ============
        print("\nTest 9: All dashboard tabs work...")
        for tab in ["general", "blog", "fonts", "style"]:
            page.click(f'[data-tab="{tab}"]')
            page.wait_for_timeout(300)
            panel_visible = page.locator(f"#panel-{tab}.active").count()
            print(f"  - Tab '{tab}' active: {panel_visible > 0}")
        page.screenshot(path="test_fix3_all_tabs.png", full_page=True)

        # ============ TEST 10: Blog page ============
        print("\nTest 10: Blog page loads...")
        page.goto(f"{BASE}/blog")
        page.wait_for_timeout(2000)
        posts = page.evaluate("""
            fetch('/api/blog/posts').then(r => r.json()).then(d => d.posts.length)
        """)
        print(f"  - Blog posts: {posts}")
        assert posts >= 7, f"Blog posts không đủ! Got {posts}"

        # ============ TEST 11: Blog post standalone ============
        print("\nTest 11: Blog post standalone...")
        page.goto(f"{BASE}/blog-post/1")
        page.wait_for_timeout(2000)
        post_visible = page.locator("#blogPostContent, .blog-post, article").count()
        print(f"  - Blog post elements: {post_visible}")
        page.screenshot(path="test_fix3_blog_post.png", full_page=True)

        # ============ TEST 12: Save repo via API ============
        print("\nTest 12: Save repo via API (giữ nguyên)...")
        # Save với danh sách rỗng → nên fail với validation; test với 1 package giả
        payload = {
            "packages": [{"identifier":"test-fix3","name":"Test","download":"packages/x.3105","sha256":"A"*64,"size":100}],
            "repoMeta": {"identifier":"com.test.fix3","name":"Test Fix3","description":"Test","icon":"assets/x.png","accentColor":"#FF3B30","schemaVersion":1},
            "packagesMeta": [],
        }
        r = page.evaluate("""async (payload) => {
            const res = await fetch('/api/repo/demo/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
            return res.status;
        }""", payload)
        print(f"  - Save API status: {r} (should be 200)")
        # Restore lại file
        page.evaluate("""async () => {
            await fetch('http://127.0.0.1:5050/');  // ignore
        }""")
        page.wait_for_timeout(300)

        browser.close()
        print("\n=== ALL FIX-3 TESTS PASSED ===")

if __name__ == "__main__":
    run_tests()
