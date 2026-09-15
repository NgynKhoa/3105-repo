"""Check what boxes are visible in the layout."""
import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))

        url = "http://127.0.0.1:5050/?slug=demo"
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(6000)

        # Check all boxes that should be on the page
        layout = await page.evaluate("""
() => {
    const ids = ['shell', 'packagesBox', 'blog-section', 'headerBox', 'repoTitle', 'siteBanner', 'themeArea', 'bgLayer'];
    return ids.map(id => {
        const el = document.getElementById(id);
        if (!el) return { id, exists: false };
        const rect = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return {
            id,
            exists: true,
            display: cs.display,
            visibility: cs.visibility,
            position: cs.position,
            opacity: cs.opacity,
            top: cs.top,
            left: cs.left,
            width: cs.width,
            height: cs.height,
            zIndex: cs.zIndex,
            backgroundColor: cs.backgroundColor,
            rect: { top: rect.top, left: rect.left, w: rect.width, h: rect.height },
        };
    });
}
        """)
        for item in layout:
            print(f"\n{item['id']}:")
            for k, v in item.items():
                if k != 'id':
                    print(f"  {k}: {v}")

        # Test clicking login button
        await page.click('#settingsBtn')
        await page.wait_for_timeout(500)
        await page.screenshot(path="c:/Users/NK/Desktop/debug_settings.png", full_page=False)

        await browser.close()


asyncio.run(main())
