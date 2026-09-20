import sys, urllib.request, re
sys.stdout.reconfigure(encoding='utf-8')

url = 'https://ngynkhoa.github.io/3105-repo/'
req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'Pragma': 'no-cache'})
html = urllib.request.urlopen(req).read().decode('utf-8')
print('Size:', len(html))
print('Has owen-000:', 'owen-000' in html)
print('Has window.PUBLIC_REPO_DATA:', 'window.PUBLIC_REPO_DATA' in html)
print('Has window.PUBLIC_MODE:', 'window.PUBLIC_MODE' in html)

idx = html.find('window.PUBLIC_REPO_DATA')
if idx >= 0:
    # Print just enough to see structure
    end = idx + 200
    print('---SNIPPET---')
    print(html[idx:end])
    print('---END---')

# Count "identifier" entries in PUBLIC_REPO_DATA area
m = re.search(r'window\.PUBLIC_REPO_DATA\s*=\s*({.*?});\s*window\.PUBLIC_REPO_OWNER', html, re.DOTALL)
if m:
    snippet = m.group(1)
    print('Public data length:', len(snippet))
    print('Ident count in data:', snippet.count('"identifier"'))
