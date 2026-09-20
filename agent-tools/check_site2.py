import sys, urllib.request, re
sys.stdout.reconfigure(encoding='utf-8')

# Bypass all caches
req = urllib.request.Request(
    'https://ngynkhoa.github.io/3105-repo/',
    headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cache-Control': 'no-cache, no-store, max-age=0',
        'Pragma': 'no-cache',
        'Accept': 'text/html,application/xhtml+xml',
    }
)
html = urllib.request.urlopen(req).read().decode('utf-8')

# Search for the HTML response cache headers
print('Size:', len(html))
print('Has owen-000:', 'owen-000' in html)
print('Has owen-trial:', 'owen-trial' in html)
print('Has window.PUBLIC_REPO_DATA:', 'window.PUBLIC_REPO_DATA' in html)

# Look for renderPackages / how it processes packages
m = re.search(r'window\.PUBLIC_REPO_DATA\s*=\s*', html)
if m:
    # Find 'packages' after PUBLIC_REPO_DATA
    snippets = html[m.start():m.start()+30000]
    pkg_count = snippets.count('"identifier"')
    print('Identifier count:', pkg_count)
