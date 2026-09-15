"""Headless browser test to capture JS errors and DOM state."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        errors = []
        page_errors = []
        requests = []

        page.on("pageerror", lambda exc: page_errors.append(f"PAGE ERROR: {exc}"))
        page.on("console", lambda msg: print(f"[console.{msg.type}]", msg.text) if msg.type in ("error", "warning") else None)
        page.on("requestfailed", lambda req: print(f"[REQ FAIL] {req.url}: {req.failure}"))

        url = "http://127.0.0.1:5050/?slug=demo"
        print(f"\n=== Loading {url} ===\n")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"navigation error: {e}")

        # Wait extra for any setTimeout(refitAll, 800/2000/4000)
        await page.wait_for_timeout(5000)

        # Check window state
        state = await page.evaluate("""
() => ({
    PUBLIC_MODE: window.PUBLIC_MODE,
    PUBLIC_REPO_SLUG: window.PUBLIC_REPO_SLUG,
    PUBLIC_REPO_OWNER: window.PUBLIC_REPO_OWNER,
    PUBLIC_REPO_OWNER_GITHUB: window.PUBLIC_REPO_OWNER_GITHUB,
    currentRepo: typeof currentRepo !== 'undefined' ? currentRepo : 'undefined',
    __frontRepoName: window.__frontRepoName,
    __currentRepoOwner: window.__currentRepoOwner,
    __isAuthOwner: window.__isAuthOwner,
    __packageDownloadPaths: window.__packageDownloadPaths,
    __downloadMode: window.__downloadMode,
    cache_packages_len: typeof cache !== 'undefined' ? cache.packages.length : 'no cache',
    renderPackages_is_function: typeof renderPackages === 'function',
    __dynamicFit_renderPackages: typeof window.__dynamicFit?.renderPackages === 'function',
    packageList_HTML_len: document.getElementById('packageList')?.innerHTML.length || 0,
    packageCount_text: document.getElementById('packageCount')?.textContent || '',
    packagesBox_height: document.getElementById('packagesBox')?.clientHeight || 0,
})
        """)
        print("\n=== WINDOW STATE ===")
        for k, v in state.items():
            print(f"  {k}: {repr(v)[:200]}")

        if page_errors:
            print("\n=== PAGE ERRORS ===")
            for e in page_errors:
                print(f"  {e}")

        await browser.close()


asyncio.run(main())
