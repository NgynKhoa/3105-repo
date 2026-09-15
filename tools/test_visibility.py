"""Check if packages are visually rendered."""
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
        await page.wait_for_timeout(5000)

        # Take a screenshot
        await page.screenshot(path="c:/Users/NK/Desktop/debug_page.png", full_page=True)

        # Check element visibility
        check = await page.evaluate("""
() => {
    const list = document.getElementById('packageList');
    const box = document.getElementById('packagesBox');
    const items = document.querySelectorAll('.pkg-item');
    const settingsBtn = document.getElementById('settingsBtn');
    return {
        packageList_exists: !!list,
        packageList_innerHTML_first200: list ? list.innerHTML.substring(0, 200) : '',
        packageList_visible: list ? getComputedStyle(list).display : '',
        packageList_offsetParent: list ? !!list.offsetParent : false,
        box_display: box ? getComputedStyle(box).display : '',
        box_visibility: box ? getComputedStyle(box).visibility : '',
        box_position: box ? getComputedStyle(box).position : '',
        box_top: box ? box.style.top || getComputedStyle(box).top : '',
        box_left: box ? box.style.left || getComputedStyle(box).left : '',
        items_count: items.length,
        first_item_visible: items[0] ? getComputedStyle(items[0]).display : '',
        first_item_offsetParent: items[0] ? !!items[0].offsetParent : false,
        first_item_top: items[0] ? items[0].getBoundingClientRect().top : 0,
        first_item_left: items[0] ? items[0].getBoundingClientRect().left : 0,
        settingsBtn_visible: settingsBtn ? getComputedStyle(settingsBtn).display : '',
    };
}
        """)
        print("\n=== VISIBILITY CHECK ===")
        for k, v in check.items():
            print(f"  {k}: {repr(v)[:300]}")

        # Count visible vs hidden
        visibility_summary = await page.evaluate("""
() => {
    const items = document.querySelectorAll('.pkg-item');
    let visible = 0, hidden = 0;
    items.forEach(it => {
        const rect = it.getBoundingClientRect();
        const visible_rect = rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.left >= 0;
        if (visible_rect) visible++; else hidden++;
    });
    return { total: items.length, visible, hidden };
}
        """)
        print(f"\nVisibility summary: {visibility_summary}")

        await browser.close()


asyncio.run(main())
