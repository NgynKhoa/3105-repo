"""Verify: Now Playing should NOT auto-cycle when src is empty."""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await ctx.new_page()

        # Capture console
        logs = []
        page.on('console', lambda msg: logs.append(f'[{msg.type}] {msg.text}'))

        print('=== Test: No auto-cycle with empty src ===')
        await page.goto('http://127.0.0.1:5050/', wait_until='networkidle', timeout=20000)
        await page.wait_for_timeout(2000)

        # Track title changes over 5s
        titles = []
        for i in range(8):
            await page.wait_for_timeout(700)
            title = await page.text_content('#mpTitle') or ''
            artist = await page.text_content('#mpArtist') or ''
            titles.append((title.strip(), artist.strip()))

        # Check how many unique titles appeared (should be ≤ 2 — initial + possible 1 error recovery)
        unique = set([t for t, _ in titles])
        print(f'  Unique titles over 5s: {len(unique)}')
        for t, a in titles[:3]:
            print(f'    {t!r} / {a!r}')
        print(f'  ... (total {len(titles)} samples)')
        if len(unique) > 2:
            print('  ❌ FAIL: titles cycling — audio error loop not fixed')
        else:
            print('  ✅ PASS: titles stable')

        # Check for audio error spam
        errors = [l for l in logs if 'audio error' in l.lower()]
        print(f'  audio-error logs: {len(errors)}')
        if len(errors) > 4:
            print('  ⚠️  too many error events — but render() should not loop now')

        # Take screenshot
        await page.screenshot(path='test_now_playing.png', full_page=False, clip={'x': 900, 'y': 200, 'width': 480, 'height': 350})

        # Verify play button does not crash
        play_btn = await page.query_selector('#mpPlay')
        if play_btn:
            try:
                await play_btn.click(timeout=2000)
                await page.wait_for_timeout(500)
                print('  ✅ Play button clickable')
            except Exception as e:
                print(f'  Play button error: {e}')

        await browser.close()

asyncio.run(main())
