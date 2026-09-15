"""Test Dashboard Music panel: badge type trong playlist list (no auth needed)."""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={'width': 1400, 'height': 900})
        page = await ctx.new_page()

        # Pre-set authenticated mode by visiting dashboard with cached cookie / using localStorage
        await page.goto('http://127.0.0.1:5050/dashboard', wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(2000)

        # Wait for dashboard to render (Login might block — try anyway via JS hijack)
        loaded_dash = await page.evaluate('''(() => {
          // Manually open Music tab if dashboard loaded
          const tab = document.querySelector('button.dash-tab[data-tab="music"]');
          if (!tab) return false;
          tab.click();
          // Inject test playlist
          window.playlist = [
            { id: 1, title: 'Demo MP3',  artist: 'Local File',  src: 'https://example.com/file.mp3',     cover: '' },
            { id: 2, title: 'YT Song',   artist: 'YouTuber',    src: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', cover: 'https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg' },
            { id: 3, title: 'Spotify Hit', artist: 'Spotify Band', src: 'https://open.spotify.com/track/0e7ipj03S05BNilyuZbArc', cover: '' },
            { id: 4, title: 'SoundCloud Mix', artist: 'SC DJ',   src: 'https://soundcloud.com/officialkodakblack/tunnel-vision', cover: '' },
          ];
          if (typeof renderTracksList === 'function') { renderTracksList(); return true; }
          return false;
        })()''')
        print(f'  Dashboard loaded + Music tab opened: {loaded_dash}')
        await page.wait_for_timeout(2000)
        # Scroll to playlist list
        await page.evaluate('document.getElementById("tracksList").scrollIntoView({block: "center"})')
        await page.wait_for_timeout(500)

        # Screenshot focused on playlist
        cnt = await page.query_selector('#tracksList')
        if cnt:
            box = await cnt.bounding_box()
            if box:
                await page.screenshot(path='test_dash_playlist_badges.png', clip={'x': max(0, box['x']-20), 'y': max(0, box['y']-20), 'width': min(1400, box['width']+40), 'height': min(900, box['height']+40)})

        # Count badges
        badge_count = await page.evaluate('document.querySelectorAll("#tracksList [title=\\"YouTube\\"], #tracksList [title=\\"Spotify\\"], #tracksList [title=\\"MP3\\"], #tracksList [title=\\"SoundCloud\\"]").length')
        print(f'  Badge count in playlist: {badge_count} (expected 4)')

        await browser.close()

asyncio.run(main())
