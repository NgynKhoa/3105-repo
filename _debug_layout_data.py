"""Debug: in ra previewLayout data trên từng URL."""
from playwright.sync_api import sync_playwright

URLS = [
    ("admin", "http://127.0.0.1:5050/"),
    ("public_static", "http://127.0.0.1:8765/"),
    ("gh_live", "https://ngynkhoa.github.io/3105-repo/"),
]

for label, url in URLS:
    print(f"\n=== {label}: {url} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        # Get previewLayout from PUBLIC_REPO_DATA / PUBLIC_ADMIN_THEME
        info = page.evaluate("""() => {
            const out = {
                PUBLIC_MODE: !!window.PUBLIC_MODE,
                PUBLIC_REPO_DATA_has_previewLayout: !!(window.PUBLIC_REPO_DATA && window.PUBLIC_REPO_DATA.previewLayout),
                PUBLIC_ADMIN_THEME_has_repo_previewLayout: !!(window.PUBLIC_ADMIN_THEME && window.PUBLIC_ADMIN_THEME.repo_previewLayout),
            };
            // Dump box keys from BOTH sources
            const layout = window.PUBLIC_ADMIN_THEME && window.PUBLIC_ADMIN_THEME.repo_previewLayout;
            if (layout) {
                out.layout_stringified = JSON.stringify(layout).substring(0, 800);
                out.layout_boxes_type = typeof layout.boxes;
                out.layout_boxes_isArray = Array.isArray(layout.boxes);
                out.layout_boxes_count = layout.boxes ? (Array.isArray(layout.boxes) ? layout.boxes.length : Object.keys(layout.boxes).length) : null;
            }
            return out;
        }""")
        for k, v in info.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in v.items():
                    print(f"    {k2}: {v2}")
            else:
                print(f"  {k}: {v}")

        browser.close()
