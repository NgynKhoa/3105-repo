"""
Check localStorage of LOCAL vs GH Pages: tìm value repo_box_blog-section_height.
"""
from playwright.sync_api import sync_playwright

LOCAL_URL = "http://127.0.0.1:5050/"
GH_URL = "https://ngynkhoa.github.io/3105-repo/"

CANDIDATE_KEYS = [
    "repo_box_blog-section_height",
    "admin_repo_box_blog-section_height",
    "user_repo_box_blog-section_height",
    "blog-section", "blog_section",
    "repo_blogHeight",
]


def get_storage(url, label):
    print(f"\n=== {label} ===")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        # Get localStorage keys
        keys = page.evaluate("() => Object.keys(localStorage)")
        print(f"  total keys: {len(keys)}")
        for k in CANDIDATE_KEYS:
            if k in keys:
                v = page.evaluate(f"() => localStorage.getItem('{k}')")
                print(f"  [{k}] = {v}")
        # Also: list all blog-related keys
        blog_keys = [k for k in keys if "blog" in k.lower()]
        print(f"  blog-related keys: {blog_keys}")
        # Get all values
        if blog_keys:
            for k in blog_keys:
                v = page.evaluate(f"() => localStorage.getItem('{k}')")
                if v and len(v) > 100:
                    v = v[:100] + "..."
                print(f"    {k} = {v}")
        # Also: get inline style height of #blog-section
        h = page.evaluate("() => { const e=document.getElementById('blog-section'); return { inline: e?.style.height, computed: getComputedStyle(e).height, attr: e?.getAttribute('style')}; }")
        print(f"  blog-section style: {h}")
        browser.close()


get_storage(LOCAL_URL, "LOCAL")
get_storage(GH_URL, "GH PAGES")
