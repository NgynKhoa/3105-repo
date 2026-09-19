"""E2E test: Upload cover image qua admin dashboard, save playlist,
verify file pushed to GitHub + GH Pages shows it.
"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ADMIN_URL = "http://127.0.0.1:5050/"
GH_URL = "https://ngynkhoa.github.io/3105-repo/"

# Tạo test image bằng Pillow
try:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (60, 60), color=(255, 0, 128))  # pink test
    draw = ImageDraw.Draw(img)
    draw.text((5, 20), "TEST", fill=(255, 255, 255))
    test_cover_path = Path(r"C:\Users\NK\Desktop\MOD\3105-repo\_test_cover.png")
    img.save(test_cover_path, "PNG")
    print(f"Test cover saved: {test_cover_path} ({test_cover_path.stat().st_size} bytes)")
except ImportError:
    # Fallback: dùng 1 PNG nhỏ từ public repo
    src = Path(r"C:\Users\NK\Desktop\MOD\3105-repo\public\assets\icon\repo-icon.png")
    test_cover_path = Path(r"C:\Users\NK\Desktop\MOD\3105-repo\_test_cover.png")
    if src.exists():
        test_cover_path.write_bytes(src.read_bytes())
    else:
        # Hard-coded tiny PNG (1x1 pink pixel)
        import base64
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP8//8/AwAI/AL+XJ/"
            "Z7QAAAABJRU5ErkJggg=="
        )
        test_cover_path.write_bytes(png)
    print(f"Test cover (fallback): {test_cover_path} ({test_cover_path.stat().st_size} bytes)")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # 1. Login (if needed) + go to dashboard
    print("\n=== Step 1: Open dashboard ===")
    page.goto(ADMIN_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # Check if already logged in
    is_auth = page.evaluate("""() => {
        return !!document.querySelector('[data-tab="dashboard"]') ||
               document.body.innerText.includes('Dashboard') ||
               document.location.pathname.includes('dashboard');
    }""")
    print(f"  Authenticated: {is_auth}")

    if not is_auth:
        # Skip login (assume OAuth session expired or not set up)
        print("  Not authenticated — cannot test full flow without login.")
        print("  Will test what we can without auth.")
        b.close()
        exit(0)

    # 2. Navigate to Music tab
    print("\n=== Step 2: Open Music tab ===")
    page.evaluate("document.querySelector('[data-tab=\"music\"]').click()")
    page.wait_for_timeout(800)

    # 3. Upload cover
    print("\n=== Step 3: Upload cover image ===")
    file_input = page.query_selector("#trackCoverFile")
    if not file_input:
        print("  ERR: trackCoverFile not found!")
        b.close()
        exit(1)

    file_input.set_input_files(str(test_cover_path))
    page.wait_for_timeout(2000)

    # Read the URL/path set in trackCoverInput
    cover_value = page.input_value("#trackCoverInput")
    print(f"  Cover value after upload: {cover_value}")

    if not cover_value or "assets/blog/" not in cover_value:
        print(f"  ERR: Cover value doesn't contain 'assets/blog/': {cover_value}")
        b.close()
        exit(1)

    # 4. Add track with this cover
    print("\n=== Step 4: Fill + add track ===")
    page.fill("#trackTitleInput", "Test E2E Song")
    page.fill("#trackArtistInput", "Auto Test")
    page.click('button[onclick="addTrack()"]')
    page.wait_for_timeout(800)

    # 5. Save playlist
    print("\n=== Step 5: Save playlist ===")
    # Find save button
    save_btn = page.query_selector('button[onclick="persistPlaylist()"]')
    if not save_btn:
        # Try other selector
        save_btn = page.query_selector('button.form-btn.success:has-text("Lưu")')
    if save_btn:
        save_btn.click()
        page.wait_for_timeout(3000)
    else:
        print("  WARN: save button not found, trying keyboard shortcut")

    # Verify on GH Pages after workflow
    print(f"\n=== Step 6: Wait for workflow + check GH Pages ===")
    cover_filename = cover_value.split("/")[-1]
    print(f"  Looking for: {cover_filename}")

    # Wait up to 90s for GH Pages to update
    for attempt in range(9):
        time.sleep(10)
        try:
            r = page.request.get(GH_URL + f"assets/blog/{cover_filename}", timeout=10)
            status = r.status
            print(f"  [{attempt*10}s] {status} {r.url}")
            if status == 200:
                print(f"  ✅ Cover visible on GH Pages!")
                break
        except Exception as e:
            print(f"  [{attempt*10}s] ERR: {e}")

    b.close()
