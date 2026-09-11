# -*- coding: utf-8 -*-
"""Reproduce the Push button issue"""
import urllib.request, json
data = json.dumps({"commit_msg": "Test push from script"}).encode()
req = urllib.request.Request(
    'http://127.0.0.1:5050/api/repo/demo/push',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=60)
    print('Status:', resp.status)
    print('Body:', resp.read().decode())
except urllib.error.HTTPError as e:
    print('HTTPError:', e.code)
    print('Body:', e.read().decode())
except Exception as e:
    print('Error:', type(e).__name__, e)
