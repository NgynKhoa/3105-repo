import json, urllib.request, urllib.error, re, os

env_path = r'c:\Users\NK\Desktop\MOD\3105-repo\.env'
pat = None
if os.path.exists(env_path):
    for line in open(env_path, encoding='utf-8', errors='replace'):
        line = line.strip()
        if line.startswith('GITHUB_PAT'):
            parts = line.split('=', 1)
            if len(parts) == 2:
                pat = parts[1].strip().strip('"').strip("'")
                break

if not pat:
    print('No PAT found'); exit(1)

# Get workflow ID
req = urllib.request.Request('https://api.github.com/repos/NgynKhoa/3105-repo/actions/workflows')
req.add_header('Authorization', 'Bearer ' + pat)
req.add_header('Accept', 'application/vnd.github.v3+json')
r = urllib.request.urlopen(req, timeout=15)
data = json.loads(r.read())
for w in data.get('workflows', []):
    if 'Build' in w['name']:
        wid = w['id']
        print('Workflow:', w['name'], 'ID:', wid)
        req2 = urllib.request.Request(
            'https://api.github.com/repos/NgynKhoa/3105-repo/actions/workflows/' + str(wid) + '/dispatches',
            data=json.dumps({'ref': 'main'}).encode(),
            headers={'Authorization': 'Bearer ' + pat, 'Accept': 'application/vnd.github.v3+json', 'Content-Type': 'application/json'}
        )
        try:
            r2 = urllib.request.urlopen(req2, timeout=15)
            print('Triggered OK! Status:', r2.status)
        except urllib.error.HTTPError as e:
            print('Error:', e.code, e.read().decode())
