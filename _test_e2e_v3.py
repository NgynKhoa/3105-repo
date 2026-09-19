"""E2E test với OAuth flow đơn giản:
- Login OAuth (giả sử user đã authorize app)
- Upload cover mới
- Save playlist
- Verify GH Pages has new cover
"""
import time
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

ADMIN_URL = "http://127.0.0.1:5050/"
GH_URL = "https://ngynkhoa.github.io/3105-repo/"

# Tạo test image
try:
    from PIL import Image, ImageDraw
    import random
    img = Image.new("RGB", (80, 80), color=(random.randint(50,255), random.randint(50,255), random.randint(50,255)))
    draw = ImageDraw.Draw(img)
    draw.text((5, 30), "E2E", fill=(255, 255, 255))
    test_cover_path = Path(r"C:\Users\NK\Desktop\MOD\3105-repo\_test_cover_e2e.png")
    img.save(test_cover_path, "PNG")
    print(f"Created test cover: {test_cover_path}")
except ImportError:
    test_cover_path = Path(r"C:\Users\NK\Desktop\MOD\3105-repo\public\assets\icon\repo-icon.png")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()

    # Bước 1: Mở admin
    print("\n=== Step 1: Open admin ===")
    page.goto(ADMIN_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)

    # Bước 2: Check auth status
    print("\n=== Step 2: Check auth ===")
    auth_info = page.evaluate("""() => ({
        url: location.href,
        hasLogin: !!document.getElementById('btnLogin'),
        hasDashboard: !!document.querySelector('[data-tab="dashboard"]'),
        isOwner: window.__isAuthOwner || false,
        bodyText: document.body.innerText.substring(0, 200)
    })""")
    print(f"  Auth info: {auth_info}")

    if auth_info['hasLogin']:
        print("  Need to login. Stop test here (OAuth needs browser interaction).")
        b.close()
        exit(0)

    if not auth_info['hasDashboard']:
        print("  Not authenticated. Try going to dashboard directly...")
        page.goto(ADMIN_URL + "dashboard", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)

    # Bước 3: Navigate to music
    print("\n=== Step 3: Open Music panel ===")
    page.evaluate("document.querySelector('[data-tab=\"music\"]')?.click()")
    page.wait_for_timeout(1000)

    panel_visible = page.evaluate("document.getElementById('panel-music')?.classList.contains('active')")
    print(f"  Music panel active: {panel_visible}")

    if not panel_visible:
        print("  Cannot access music panel — need login")
        b.close()
        exit(0)

    # Bước 4: Upload cover
    print("\n=== Step 4: Upload cover image ===")
    file_input = page.query_selector("#trackCoverFile")
    if file_input:
        file_input.set_input_files(str(test_cover_path))
        page.wait_for_timeout(2000)
        cover_value = page.input_value("#trackCoverInput")
        print(f"  Cover value: {cover_value}")
    else:
        print("  ERR: trackCoverFile not found")
        b.close()
        exit(1)

    # Bước 5: Add track
    print("\n=== Step 5: Add new track with new cover ===")
    page.fill("#trackTitleInput", "E2E Auto Push Test")
    page.fill("#trackArtistInput", "Test Bot")
    page.click('button[onclick="addTrack()"]')
    page.wait_for_timeout(1000)

    # Bước 6: Save playlist (triggers /api/admin-settings → push binary)
    print("\n=== Step 6: Save playlist ===")
    # Save via persistPlaylist button
    page.evaluate("persistPlaylist()")
    page.wait_for_timeout(5000)

    # Check response
    print("\n=== Step 7: Verify cover on GH Pages ===")
    if "assets/blog/" in cover_value:
        filename = cover_value.split("/")[-1]
        for attempt in range(12):
            time.sleep(10)
            try:
                r = page.request.get(GH_URL + f"assets/blog/{filename}", timeout=10)
                print(f"  [{attempt*10}s] {r.status} {filename}")
                if r.status == 200:
                    print(f"  ✅ Cover '{filename}' is live on GH Pages!")
                    break
            except Exception as e:
                print(f"  [{attempt*10}s] ERR: {e}")
    else:
        print(f"  Cover URL doesn't have 'assets/blog/': {cover_value}")

    b.close()
