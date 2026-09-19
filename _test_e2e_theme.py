"""
End-to-end test: đổi theme + push + verify GH Pages.
Giả lập admin UI autoSave flow nhưng qua git CLI (không cần browser).
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(r"C:\Users\NK\Desktop\MOD\3105-repo")
SETTINGS = REPO / ".3105" / "admin-settings.json"
GH_PAGES_URL = "https://ngynkhoa.github.io/3105-repo/"
GH_RAW_URL = "https://raw.githubusercontent.com/NgynKhoa/3105-repo/main/.3105/admin-settings.json"

NEW_THEME = sys.argv[1] if len(sys.argv) > 1 else "pink"
NEW_SHADOW = sys.argv[2] if len(sys.argv) > 2 else "cyan"

print(f"=== Test plan: theme={NEW_THEME} shadow={NEW_SHADOW} ===\n")

# Step 1: Đọc local hiện tại
with open(SETTINGS, "r", encoding="utf-8") as f:
    data = json.load(f)
print(f"[1] BEFORE: theme={data.get('theme')} shadow={data.get('shadowTheme')}")
print(f"    admin_theme={data.get('admin_theme')} admin_shadowTheme={data.get('admin_shadowTheme')}")
print(f"    repo_theme={data.get('repo_theme')} repo_shadowTheme={data.get('repo_shadowTheme')}")

# Step 2: Sửa
data["theme"] = NEW_THEME
data["shadowTheme"] = NEW_SHADOW
data["admin_theme"] = NEW_THEME
data["admin_shadowTheme"] = NEW_SHADOW
data["repo_theme"] = NEW_THEME
data["repo_shadowTheme"] = NEW_SHADOW
data["shadow_theme"] = NEW_SHADOW
with open(SETTINGS, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"\n[2] EDITED: theme={NEW_THEME} shadow={NEW_SHADOW}")

# Step 3: Git add + commit + push
subprocess.run(["git", "add", ".3105/admin-settings.json"], cwd=REPO, check=True)
status = subprocess.run(["git", "status", "--porcelain", ".3105/admin-settings.json"],
                       cwd=REPO, capture_output=True, text=True)
if not status.stdout.strip():
    print("[3] SKIP: nothing to commit (local == remote)")
else:
    msg = f"chore(admin-settings): test theme={NEW_THEME} shadow={NEW_SHADOW}"
    subprocess.run(["git", "commit", "-m", msg], cwd=REPO, check=True)
    print(f"[3] COMMITTED: {msg}")

# Stash oauth if exists, pull rebase, push, pop stash
stash_r = subprocess.run(
    ["git", "stash", "push", "-m", "oauth-tmp", "--", ".oauth_cache/"],
    cwd=REPO, capture_output=True, text=True
)
pull_r = subprocess.run(["git", "pull", "--rebase"], cwd=REPO, capture_output=True, text=True)
print(f"[4] PULL: rc={pull_r.returncode}")
if pull_r.returncode != 0:
    print(f"    stderr: {pull_r.stderr[:200]}")

push_r = subprocess.run(["git", "push"], cwd=REPO, capture_output=True, text=True)
print(f"[5] PUSH: rc={push_r.returncode}")
print(f"    stdout: {push_r.stdout[:200]}")
if push_r.returncode != 0:
    print(f"    stderr: {push_r.stderr[:200]}")

# Pop stash
subprocess.run(["git", "stash", "pop"], cwd=REPO, capture_output=True, text=True)

if push_r.returncode != 0:
    print("[FAIL] Push failed")
    sys.exit(1)

# Step 4: Verify remote
print(f"\n[6] Verifying remote...")
time.sleep(3)
try:
    with urllib.request.urlopen(GH_RAW_URL, timeout=15) as r:
        remote = json.loads(r.read().decode("utf-8"))
    print(f"    remote theme = {remote.get('theme')}")
    print(f"    remote shadowTheme = {remote.get('shadowTheme')}")
except Exception as e:
    print(f"    ERR: {e}")

# Step 5: Check workflow triggered
print(f"\n[7] Checking workflow runs...")
time.sleep(2)
r = subprocess.run(
    ["gh", "run", "list", "--workflow=build-public.yml", "--limit", "3"],
    capture_output=True, text=True
)
print(r.stdout[:600])

# Step 6: Verify GH Pages (chờ workflow xong)
print(f"\n[8] Waiting for workflow to finish (max 3min)...")
for i in range(18):
    time.sleep(10)
    r = subprocess.run(
        ["gh", "run", "list", "--workflow=build-public.yml", "--limit", "1"],
        capture_output=True, text=True
    )
    line = r.stdout.splitlines()[0] if r.stdout else ""
    print(f"  [{i*10}s] {line[:120]}")
    if "completed" in line and "success" in line:
        print(f"\n[9] Workflow SUCCESS! Fetching GH Pages...")
        time.sleep(5)
        try:
            with urllib.request.urlopen(GH_PAGES_URL, timeout=15) as r:
                html = r.read().decode("utf-8")
            idx = html.find("PUBLIC_ADMIN_THEME")
            if idx >= 0:
                snippet = html[idx:idx+500]
                print(f"  {snippet}")
                if f'"theme": "{NEW_THEME}"' in snippet:
                    print(f"\n[SUCCESS] GH Pages now shows theme={NEW_THEME}")
                elif f'"theme":' in snippet:
                    import re
                    m = re.search(r'"theme":\s*"([^"]+)"', snippet)
                    if m:
                        print(f"\n[INFO] GH Pages shows theme={m.group(1)} (not {NEW_THEME} yet)")
        except Exception as e:
            print(f"  ERR fetching GH Pages: {e}")
        break
    elif "completed" in line and "failure" in line:
        print(f"\n[FAIL] Workflow failed!")
        break
