"""
Đồng bộ local admin-settings.json → GitHub bằng cách gọi endpoint Flask.
Script này giả lập việc admin UI autoSave, nhưng KHÔNG cần browser/cookie
vì nó push trực tiếp qua git CLI.

Dùng để test end-to-end mà không cần thao tác trên browser.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\Users\NK\Desktop\MOD\3105-repo")
SETTINGS = REPO / ".3105" / "admin-settings.json"

print("=== Step 1: Show current LOCAL admin-settings.json ===")
with open(SETTINGS, "r", encoding="utf-8") as f:
    local = json.load(f)
print(f"  theme        = {local.get('theme')}")
print(f"  shadow_theme = {local.get('shadow_theme')}")
print(f"  dark_mode    = {local.get('dark_mode')}")
print(f"  transparency = {local.get('transparency')}")

print("\n=== Step 2: Show current REMOTE admin-settings.json (GitHub) ===")
import urllib.request
try:
    url = "https://raw.githubusercontent.com/NgynKhoa/3105-repo/main/.3105/admin-settings.json"
    with urllib.request.urlopen(url, timeout=15) as r:
        remote = json.loads(r.read().decode("utf-8"))
    print(f"  theme        = {remote.get('theme')}")
    print(f"  shadow_theme = {remote.get('shadow_theme')}")
    print(f"  dark_mode    = {remote.get('dark_mode')}")
    print(f"  transparency = {remote.get('transparency')}")
except Exception as e:
    print(f"  ERR: {e}")
    remote = None

if remote and remote.get("theme") == local.get("theme"):
    print("\n[OK] Local and remote themes match. Nothing to sync.")
    sys.exit(0)

print(f"\n=== Step 3: Git add/commit/push local settings to GitHub ===")
# Stage
subprocess.run(["git", "add", ".3105/admin-settings.json"], cwd=REPO, check=True)
# Show diff
subprocess.run(["git", "diff", "--cached", "--stat"], cwd=REPO, check=True)

# Commit (only if there's staged change)
status = subprocess.run(["git", "status", "--porcelain", ".3105/admin-settings.json"],
                       cwd=REPO, capture_output=True, text=True)
if "M " in status.stdout or "A " in status.stdout:
    msg = f"chore(admin-settings): sync {local.get('theme')} from local"
    subprocess.run(["git", "commit", "-m", msg], cwd=REPO, check=True)
    print(f"\n[OK] Committed: {msg}")
else:
    print("\n[skip] Nothing to commit")

# Pull rebase then push
print("\n=== Step 4: Pull rebase + push ===")
r = subprocess.run(["git", "pull", "--rebase"], cwd=REPO, capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    print(f"[warn] pull rebase failed: {r.stderr}")

r = subprocess.run(["git", "push"], cwd=REPO, capture_output=True, text=True)
print(r.stdout)
if r.returncode != 0:
    print(f"[ERR] push failed: {r.stderr}")
    sys.exit(1)
print("[OK] Pushed to GitHub")

print("\n=== Step 5: Verify remote ===")
import time
time.sleep(2)
try:
    with urllib.request.urlopen(url, timeout=15) as r:
        remote_after = json.loads(r.read().decode("utf-8"))
    print(f"  theme (after) = {remote_after.get('theme')}")
    if remote_after.get("theme") == local.get("theme"):
        print(f"\n[SUCCESS] Local and remote are now in sync: theme={remote_after.get('theme')}")
    else:
        print(f"\n[FAIL] Still different: local={local.get('theme')} remote={remote_after.get('theme')}")
except Exception as e:
    print(f"  ERR: {e}")
