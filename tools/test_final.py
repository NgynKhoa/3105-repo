"""Test GH Pages production URL after fix."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))
        page.on("console", lambda msg: print(f"[{msg.type}]", msg.text[:200]) if msg.type in ("error", "warning", "log") else None)

        url = "http://127.0.0.1:5050/?slug=demo"
        print(f"\n=== Loading {url} ===\n")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        # Wait LONGER for fetchRepoJsonForAnon to complete (it fires after fetchAuthState)
        await page.wait_for_timeout(10000)

        state = await page.evaluate("""
() => ({
    __isAuthOwner: window.__isAuthOwner,
    __currentRepoOwner: window.__currentRepoOwner,
    __packageReleases: window.__packageReleases?.length || 0,
    __packageDownloadPaths: window.__packageDownloadPaths?.length || 0,
    __downloadMode: window.__downloadMode,
    __adminDefaults: window.__adminDefaults,
    pkgCount: document.getElementById('packageCount')?.textContent,
    packageList_items: document.querySelectorAll('.pkg-item').length,
    download_btns: document.querySelectorAll('.neon-download').length,
    find_btns: document.querySelectorAll('.neon-download-ghost').length,
})
        """)
        print("=== STATE ===")
        for k, v in state.items():
            print(f"  {k}: {repr(v)[:200]}")

        await page.screenshot(path="c:/Users/NK/Desktop/debug_final.png", full_page=True)

        await browser.close()


asyncio.run(main())
