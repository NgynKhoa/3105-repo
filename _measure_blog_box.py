"""
Measure Blog box dimensions on:
  - Admin local (Flask): http://127.0.0.1:5050/
  - Public local (served from public/): http://127.0.0.1:8765/
  - GH Pages live: https://ngynkhoa.github.io/3105-repo/

Compare results to find any difference.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ADMIN_URL = "http://127.0.0.1:5050/"
PUBLIC_URL = "http://127.0.0.1:8765/"
GH_URL = "https://ngynkhoa.github.io/3105-repo/"
RESULT_FILE = Path(r"C:\Users\NK\Desktop\MOD\3105-repo\_blog_box_diff.json")

CANDIDATE_SELECTORS = [
    '[id^="blog-section"]',
    '#blogList',
]


def measure(url: str, label: str, viewport=(1280, 900)) -> dict:
    """Open `url`, screenshot, return box measurements."""
    print(f"\n[{label}] opening {url} ...", flush=True)
    result = {"url": url, "label": label, "boxes": {}, "viewport": viewport}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)  # chờ layout apply + render blog

        shot_path = Path(f"_screenshot_{label}.png")
        page.screenshot(path=str(shot_path), full_page=True)
        print(f"  screenshot: {shot_path}")

        for sel in CANDIDATE_SELECTORS:
            boxes = page.query_selector_all(sel)
            if not boxes:
                continue
            for i, b in enumerate(boxes):
                try:
                    bb = b.bounding_box()
                    if not bb:
                        continue
                    inline_h = page.evaluate(f"(sel) => document.querySelector(sel)?.style.height || ''", sel)
                    result["boxes"][f"{sel}[{i}]"] = {
                        "bbox": bb,
                        "inline_height": inline_h,
                    }
                except Exception as e:
                    print(f"  err {sel}[{i}]: {e}")

        # Debug: list blog-related localStorage keys + style.height
        ls_keys = page.evaluate("() => Object.keys(localStorage)")
        blog_keys = [k for k in ls_keys if "blog" in k.lower() or "repo_box" in k.lower()]
        result["blog_storage_keys"] = blog_keys
        blog_style = page.evaluate("() => { const e=document.getElementById('blog-section'); return e ? {inline: e.style.height, attr: e.getAttribute('style')} : null; }")
        result["blog_section_style"] = blog_style

        browser.close()
    return result


def main():
    out = {}
    for url, label in [(ADMIN_URL, "admin"), (PUBLIC_URL, "public_static"), (GH_URL, "gh_live")]:
        try:
            out[label] = measure(url, label)
        except Exception as e:
            out[label + "_error"] = str(e)

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n=== Results saved to {RESULT_FILE} ===\n")
    for label in ("admin", "public_static", "gh_live"):
        if label not in out:
            print(f"  {label}: ERROR - {out.get(label+'_error')}")
            continue
        d = out[label]
        print(f"=== {label.upper()} ===")
        print(f"  blog-section style: {d.get('blog_section_style')}")
        for k, v in d.get("boxes", {}).items():
            bb = v.get("bbox") or {}
            print(f"  {k}: bbox=({bb.get('x')},{bb.get('y')}) {bb.get('width')}x{bb.get('height')}  inline_h={v.get('inline_height')}")


if __name__ == "__main__":
    main()
