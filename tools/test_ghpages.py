"""Test GH Pages production URL."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))
        page.on("console", lambda msg: print(f"[{msg.type}]", msg.text[:200]) if msg.type in ("error", "warning", "log") else None)

        url = "https://ngynkhoa.github.io/3105-repo/"
        print(f"\n=== Loading {url} ===\n")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"navigation error: {e}")

        await page.wait_for_timeout(5000)

        state = await page.evaluate("""
() => ({
    PUBLIC_MODE: window.PUBLIC_MODE,
    PUBLIC_REPO_DATA_exists: !!window.PUBLIC_REPO_DATA,
    PUBLIC_REPO_DATA_packages_count: window.PUBLIC_REPO_DATA?.packages?.length,
    pkgCount: document.getElementById('packageCount')?.textContent,
    packageList_items: document.querySelectorAll('.pkg-item').length,
    first_pkg_id: document.querySelector('.pkg-item')?.dataset.id,
})
        """)
        print("=== GH PAGES STATE ===")
        for k, v in state.items():
            print(f"  {k}: {repr(v)[:200]}")

        await page.screenshot(path="c:/Users/NK/Desktop/debug_ghpages.png", full_page=True)
        await browser.close()


asyncio.run(main())
