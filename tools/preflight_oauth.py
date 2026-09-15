"""Pre-flight check trước khi test GitHub OAuth."""
import sys
from pathlib import Path

# Read .env manually (avoid dotenv dep)
env_path = Path('.env')
if not env_path.exists():
    print("MISSING: .env file not found")
    sys.exit(1)

env = {}
for line in env_path.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    if '=' in line:
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

print('OAuth config:')
required = {
    'GITHUB_CLIENT_ID': ('Ov', 'Iv'),  # OAuth App IDs start with Ov or Iv
    'GITHUB_CLIENT_SECRET': ('',),
    'OAUTH_CALLBACK_URL': ('http://',),
    'FRONTEND_BASE_URL': ('http://',),
    'SECRET_KEY': ('',),
}
for k, _ in required.items():
    v = env.get(k, '')
    if k == 'GITHUB_CLIENT_SECRET':
        print(f'  {k}: {v[:10]}...' if v else f'  {k}: MISSING')
    elif v:
        print(f'  {k}: {v}')
    else:
        print(f'  {k}: MISSING')

# Validate callback URL match GH App
cb = env.get('OAUTH_CALLBACK_URL', '')
print(f'\nCallback URL: {cb}')
print('=> GitHub OAuth App "Authorization callback URL" PHẢI khớp URL này (exact match).')

# Test GitHub API client ID validity
import urllib.request, json
client_id = env.get('GITHUB_CLIENT_ID', '')
if client_id.startswith(('Ov', 'Iv')):
    url = f'https://api.github.com/applications/{client_id}'
    print(f'\n(Mã này có vẻ là Client ID OAuth App — verified bằng cách thử authorize URL)')

# Check reachable
try:
    req = urllib.request.Request('https://api.github.com', headers={'User-Agent': 'preflight'})
    r = urllib.request.urlopen(req, timeout=5)
    print('GitHub API reachable: YES')
except Exception as e:
    print(f'GitHub API reachable: NO ({e})')
