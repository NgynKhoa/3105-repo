# -*- coding: utf-8 -*-
"""Reproduce full save+push flow"""
import urllib.request, json
import subprocess
import sys

print("=== STEP 1: git status ===")
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
r = subprocess.run(['git', '-C', r'c:\Users\NK\Desktop\MOD\3105-repo', 'status'], capture_output=True, text=True)
print(r.stdout)
print("stderr:", r.stderr)

print("\n=== STEP 2: Front Repo render (verifies API calls) ===")
# Visit front repo to get html
req = urllib.request.Request('http://127.0.0.1:5050/')
resp = urllib.request.urlopen(req, timeout=10)
html = resp.read().decode()
print("Status:", resp.status)
print("Length:", len(html))
print("Has app.js:", 'app.js' in html)

print("\n=== STEP 3: simulate save+push via API ===")
# 1. Save YAML
data = json.dumps({"repoMeta": {}, "packages": [], "packagesMeta": []}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:5050/api/repo/demo/save',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print("SAVE: Status", resp.status)
    print("Body:", resp.read().decode()[:300])
except urllib.error.HTTPError as e:
    print("SAVE: HTTPError", e.code)
    print("Body:", e.read().decode())

# 2. Push
data = json.dumps({"commit_msg": "Test push from script"}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:5050/api/repo/demo/push',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=60)
    print("PUSH: Status", resp.status)
    print("Body:", resp.read().decode()[:300])
except urllib.error.HTTPError as e:
    print("PUSH: HTTPError", e.code)
    print("Body:", e.read().decode()[:300])
