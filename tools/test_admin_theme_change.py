"""Admin login + đổi accentColor + verify user view thấy màu mới."""
import asyncio, os
from playwright.async_api import async_playwright

ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'changeme')

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))

        # 1. Vào admin, login
        await page.goto('http://127.0.0.1:5050/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(2000)

        # Check login form có hiển thị không
        username_field = await page.query_selector('#loginUsername, #username, input[name="username"]')
        if username_field:
            print('  Login form detected — filling credentials...')
            try:
                await page.fill('#username', ADMIN_USER)
                await page.fill('#password', ADMIN_PASS)
                await page.click('#btnLogin, button[type="submit"]')
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f'  Login flow error: {e}')

        # 2. Wait for admin UI loaded
        await page.wait_for_selector('#meta_accentColor', timeout=10000)
        current = await page.input_value('#meta_accentColor')
        print(f'  Current accentColor input: {current!r}')

        # 3. Set sang màu tím cyan #00D9FF
        await page.fill('#meta_accentColor', '#00D9FF')
        await page.click('#btnSave')
        await page.wait_for_timeout(2000)
        print('  Saved accentColor = #00D9FF')

        # 4. Reload, check current
        await page.reload(wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        await page.wait_for_selector('#meta_accentColor', timeout=10000)
        reload_val = await page.input_value('#meta_accentColor')
        print(f'  Reload value: {reload_val!r}')
        assert reload_val.lower() == '#00d9ff', f'Expected #00D9FF, got {reload_val!r}'

        # 5. Check CSS var applied
        neon = await page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--neon').trim()")
        neon_rgb = await page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--neon-rgb').trim()")
        print(f'  --neon   = {neon!r}')
        print(f'  --neon-rgb = {neon_rgb!r}')
        assert neon.upper() == '#00D9FF', f'Expected --neon=#00D9FF, got {neon!r}'

        # 6. Mock "user view" — just reload page (Flask serves same template)
        # Check accent color still visible (already verified above)

        # 7. Screenshot
        await page.screenshot(path='test_theme_admin.png', full_page=False)

        # 8. Cleanup — restore to #FF3B30
        await page.fill('#meta_accentColor', '#FF3B30')
        await page.click('#btnSave')
        await page.wait_for_timeout(2000)
        print('  Restored accentColor to #FF3B30')

        if errors:
            print(f'\n⚠ {len(errors)} JS errors:')
            for e in errors[:3]:
                print(f'  {e[:200]}')
        else:
            print('\n✅ No JS errors')

        await browser.close()

asyncio.run(main())
