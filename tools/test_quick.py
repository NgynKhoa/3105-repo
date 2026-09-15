import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context()
        page = await ctx.new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text[:200]) if "error" in m.type.lower() else None)

        # Test 1: Front repo loads
        await page.goto("http://127.0.0.1:5050/?slug=demo")
        await page.wait_for_load_state("networkidle", timeout=15000)
        title = await page.title()
        print("[OK] Front repo loaded:", title[:60])

        # Test 2: Settings opens
        try:
            await page.click("#settingsBtn", timeout=5000)
            await page.wait_for_timeout(1000)
            menu_visible = await page.is_visible("#settingsMenu")
            print("[OK] Settings menu opens:", menu_visible)
            await page.click("#closeSettings", timeout=3000)
        except Exception as e:
            print("[FAIL] Settings:", e)

        # Test 3: Download URL for packages
        try:
            dl_btns = page.locator("button.download-btn")
            cnt = await dl_btns.count()
            print("[OK] Download buttons found:", cnt)
            if cnt > 0:
                href = await dl_btns.first.get_attribute("href")
                print("[OK] Download href:", (href or "NO HREF")[:100])
        except Exception as e:
            print("[FAIL] Download:", e)

        # Test 4: Blog list
        try:
            blog_cards = page.locator(".blog-card")
            count = await blog_cards.count()
            print("[OK] Blog cards:", count)
        except Exception as e:
            print("[FAIL] Blog:", e)

        # Test 5: Dashboard Links tab
        await page.goto("http://127.0.0.1:5050/dashboard")
        await page.wait_for_load_state("networkidle", timeout=10000)
        try:
            links_tab = page.locator('[data-tab="links"]')
            await links_tab.wait_for(timeout=5000)
            print("[OK] Links tab visible:", await links_tab.is_visible())
            await links_tab.click()
            await page.wait_for_timeout(500)
            links_list = page.locator("#linksList")
            print("[OK] Links list present:", await links_list.is_visible())
        except Exception as e:
            print("[FAIL] Links tab:", e)

        if errors:
            print("[JS ERRORS]:", errors[:3])

        await browser.close()

asyncio.run(test())
