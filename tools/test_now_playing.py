"""Verify Now Playing UI: title size, no dot in disc, spin pause-resume."""
import asyncio, time
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await ctx.new_page()

        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))

        print('=== Test Now Playing UI ===')
        # Use localhost Flask (since OAuth not needed to render index.html)
        await page.add_init_script('''
            window.PUBLIC_PLAYLIST = [
              { id: 1, title: 'Synthwave Drift', artist: 'Owen · 80s Mix', src: 'https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav', cover: '' },
            ];
        ''')
        await page.goto('http://127.0.0.1:5050/', wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(4000)

        # 1. Title font-size
        title_fs = await page.evaluate('parseFloat(getComputedStyle(document.getElementById("mpTitle")).fontSize)')
        print(f'  mpTitle font-size: {title_fs}px (expected ~12.5px = 0.78rem × 16px)')
        assert 11.5 <= title_fs <= 13.5, f'Title size out of range: {title_fs}'

        # 2. Dot ::after không còn
        dot_styles = await page.evaluate('''(() => {
          const el = document.querySelector('.mp-cover-inner');
          const s = getComputedStyle(el, '::after');
          return { content: s.content, displayContent: s.content === 'none' || s.content === 'normal' };
        })()''')
        print(f'  .mp-cover-inner::after content: {dot_styles["content"]!r}')

        # 3. Spin pause giữ góc
        print('  Testing spin pause-keeps-angle:')
        await page.click('#mpPlay', timeout=2000)
        await page.wait_for_timeout(1500)  # let it spin 1.5s
        angle_before = await page.evaluate('parseFloat(document.getElementById("mpCover").style.transform.replace(/[^0-9.\\-]/g,"") || "0")')
        print(f'    Angle after 1.5s playing: {angle_before:.2f}deg')

        await page.click('#mpPlay', timeout=2000)
        await page.wait_for_timeout(1500)  # 1.5s paused
        angle_after_pause = await page.evaluate('parseFloat(document.getElementById("mpCover").style.transform.replace(/[^0-9.\\-]/g,"") || "0")')
        print(f'    Angle after 1.5s PAUSED: {angle_after_pause:.2f}deg')

        # Should not reset to ~0 after pause
        # Allow tiny rounding (CSS pixel rounding of large degrees)
        is_held = (angle_after_pause > 5 and abs(angle_after_pause - angle_before) < 5)
        print(f'    Hold during pause: {is_held} (diff={abs(angle_after_pause - angle_before):.2f})')

        # Resume
        await page.click('#mpPlay', timeout=2000)
        await page.wait_for_timeout(800)
        angle_resumed = await page.evaluate('parseFloat(document.getElementById("mpCover").style.transform.replace(/[^0-9.\\-]/g,"") || "0")')
        moved = angle_resumed > angle_after_pause
        print(f'    Resume spin: angle went {angle_after_pause:.2f} → {angle_resumed:.2f} (grew: {moved})')

        # 4. Screenshot
        await page.click('#mpPlay', timeout=2000)  # pause again for clean shot
        await page.wait_for_timeout(800)
        box = await page.evaluate('(() => { const r = document.getElementById("music-player").getBoundingClientRect(); return {x: r.x, y: r.y, width: r.width, height: r.height}; })()')
        await page.screenshot(path='test_now_playing.png', clip={'x': max(0, box['x']-10), 'y': max(0, box['y']-10), 'width': box['width']+20, 'height': box['height']+20})

        if errors:
            print(f'\n⚠ Errors: {len(errors)}')
            for e in errors[:3]:
                print(f'  {e[:120]}')
        else:
            print('\n✅ No JS errors')

        await browser.close()

asyncio.run(main())
