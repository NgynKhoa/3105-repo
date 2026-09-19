"""Unit test the auto-push logic trong merge_admin_settings.
Mock fetch_admin_settings + gh_write_file + gh_write_binary_file để verify
flow detect cover mới + push binary.
"""
import sys
import json
import pathlib
import tempfile
from unittest.mock import MagicMock, patch

sys.path.insert(0, r"C:\Users\NK\Desktop\MOD\3105-repo")

# Tạo test cover file
TEST_DIR = pathlib.Path(tempfile.mkdtemp(prefix="3105_test_"))
TEST_COVER = TEST_DIR / "assets" / "blog" / "abc123.png"
TEST_COVER.parent.mkdir(parents=True, exist_ok=True)
TEST_COVER.write_bytes(b"\x89PNG fake content for test")

print(f"Test cover at: {TEST_COVER}")

# Tạo settings có cover path tương đối
sample_settings = {
    "theme": "yellow",
    "playlist": [
        {"id": 1, "title": "Song 1", "artist": "A", "src": "", "cover": "assets/blog/abc123.png"},
        {"id": 2, "title": "Song 2", "artist": "B", "src": "", "cover": "https://external.com/cover.jpg"},  # skip
        {"id": 3, "title": "Song 3", "artist": "C", "src": "", "cover": ""},  # skip
    ],
    "other_key": "should be kept",
}

# Patch _ROOT trong admin_settings để trỏ vào test dir
import admin.admin_settings as as_mod
as_mod._ROOT = TEST_DIR

# Mock các helper bên ngoài
captured = {"pushed_assets": [], "wrote_file": None, "bake_called": False}

def mock_fetch_admin_settings(full_name, token):
    return {"old_key": "value"}  # Existing settings

def mock_gh_write_file(*, token, full_name, path, content, commit_message, mode):
    captured["wrote_file"] = {"path": path, "content": content, "mode": mode}
    return {"ok": True, "commit_sha": "abc123", "commit_url": "https://..."}

def mock_gh_write_binary_file(*, token, full_name, path, content, commit_message, mode):
    captured["pushed_assets"].append({
        "path": path, "size": len(content), "mode": mode, "msg": commit_message,
    })
    return {"ok": True, "commit_sha": "binary_sha"}

def mock_bake_public_defaults():
    captured["bake_called"] = True
    return True, "bake ok"

# Mock login/auth
def mock_login_required(f):
    return f
def mock_get_current_token():
    return "fake_token"
def mock_get_owned_repos():
    return [{"slug": "demo", "full_name": "NgynKhoa/3105-repo"}]

# Apply patches
as_mod.gh_write_file = mock_gh_write_file
as_mod.gh_write_binary_file = mock_gh_write_binary_file
as_mod._bake_public_defaults = mock_bake_public_defaults
as_mod.fetch_admin_settings = mock_fetch_admin_settings

import admin.auth as auth_mod
auth_mod.login_required = mock_login_required
auth_mod.get_current_token = mock_get_current_token
auth_mod.get_owned_repos = mock_get_owned_repos
as_mod.login_required = mock_login_required
as_mod.get_current_token = mock_get_current_token
as_mod.auth_get_owned_repos = mock_get_owned_repos

# Tạo mock app
from flask import Flask
app = Flask(__name__)
as_mod.register_admin_settings_routes(app)

# Test client
with app.test_client() as c:
    resp = c.post("/api/admin-settings-merge", json={
        "slug": "demo",
        "patch": sample_settings,
        "mode": "direct",
    })
    data = resp.get_json()

print("\n=== RESULT ===")
print(f"Status: {resp.status_code}")
print(f"Response: ok={data.get('ok')}")
print(f"Wrote file: {captured['wrote_file'] is not None}")
print(f"Push assets count: {len(captured['pushed_assets'])}")
for a in captured["pushed_assets"]:
    print(f"  - {a}")
print(f"Bake called: {captured['bake_called']}")
print(f"Errors: {data.get('assets_push_errors', [])}")
print(f"\nFinal merged settings keys: {list(data.get('settings', {}).keys())}")
print(f"Old key kept: {data.get('settings', {}).get('old_key')}")
print(f"New playlist: {len(data.get('settings', {}).get('playlist', []))} tracks")

# Verify assertions
expected_paths = ["assets/blog/abc123.png"]
actual_paths = [a["path"] for a in captured["pushed_assets"]]
assert actual_paths == expected_paths, f"Expected {expected_paths}, got {actual_paths}"
assert captured["wrote_file"] is not None, "admin-settings should be written"
assert captured["bake_called"], "bake_public_defaults should be called"
assert "pushed_assets" in data, "response should include pushed_assets"
print("\n✅ ALL ASSERTIONS PASSED")
