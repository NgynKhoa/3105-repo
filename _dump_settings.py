#!/usr/bin/env python3
"""Dump all repo settings from localStorage on the running admin server."""
import json, base64

# We can read them from the browser via an API endpoint.
# Since we can't access browser localStorage from Python directly,
# we expose a helper endpoint via the running Flask app.
# Alternative: just read from .3105/admin-settings.json on disk (what's been synced).
# The user wants settings from Front / Dashboard UI - let's check what's actually
# been saved by examining the Flask session/OAuth state and the admin-settings.json.

# Actually, the best approach is to add a simple /api/local-storage-dump endpoint
# to the running server. But since we can't modify the server right now,
# let's check what settings are currently in .3105/admin-settings.json on disk.
import pathlib, json

local_settings = pathlib.Path('.3105/admin-settings.json')
if local_settings.exists():
    data = json.loads(local_settings.read_text(encoding='utf-8'))
    print("=== .3105/admin-settings.json (LOCAL disk) ===")
    for k, v in sorted(data.items()):
        print(f"  {k}: {json.dumps(v)[:80]}")
else:
    print("Local admin-settings.json not found")

# Also check what the remote GitHub has
print()
print("NOTE: To get ACTUAL localStorage values from the browser running at")
print("      http://127.0.0.1:5050/, the server needs to expose them.")
print("      Add this to admin/app.py:")
print()
print("  @app.route('/api/local-storage-dump', methods=['POST'])")
print("  @login_required")
print("  def dump_local_storage():")
print("      data = request.json or {}")
print("      return jsonify({'ok': True, 'saved': data})")
print()
print("Then use the browser console:")
print("  fetch('/api/local-storage-dump', {method:'POST',")
print("    headers:{'Content-Type':'application/json'},")
print("    body: JSON.stringify(Object.fromEntries(")
print("      Object.keys(localStorage).map(k => [k, localStorage.getItem(k)])")
print("    ))}).then(r=>r.json()).then(console.log)")
