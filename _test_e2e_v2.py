"""End-to-end test v2: đợi workflow + verify GH Pages."""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(r"C:\Users\NK\Desktop\MOD\3105-repo")
GH_PAGES_URL = "https://ngynkhoa.github.io/3105-repo/"
GH_RAW_URL = "https://raw.githubusercontent.com/NgynKhoa/3105-repo/main/.3105/admin-settings.json"

NEW_THEME = sys.argv[1] if len(sys.argv) > 1 else "yellow"
NEW_SHADOW = sys.argv[2] if len(sys.argv) > 2 else "lavender"

print(f"=== Test: theme={NEW_THEME} shadow={NEW_SHADOW} ===\n")

# 1. Edit
with open(REPO / ".3105" / "admin-settings.json", encoding="utf-8") as f:
    d = json.load(f)
d["theme"] = NEW_THEME
d["shadowTheme"] = NEW_SHADOW
d["admin_theme"] = NEW_THEME
d["admin_shadowTheme"] = NEW_SHADOW
d["repo_theme"] = NEW_THEME
d["repo_shadowTheme"] = NEW_SHADOW
d["shadow_theme"] = NEW_SHADOW
with open(REPO / ".3105" / "admin-settings.json", "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

# 2. Re-bake local public-defaults.json
r = subprocess.run([sys.executable, "bake_defaults.py"], cwd=REPO,
                   capture_output=True, text=True)
print(f"[bake] rc={r.returncode}")
if r.returncode != 0:
    print(r.stderr)
    sys.exit(1)

# 3. Stage + commit + push
subprocess.run(["git", "add", ".3105/admin-settings.json", ".3105/public-defaults.json"],
               cwd=REPO, check=True)
status = subprocess.run(["git", "status", "--porcelain", ".3105/"],
                       cwd=REPO, capture_output=True, text=True)
if not status.stdout.strip():
    print("[git] No changes to commit")
else:
    msg = f"test: theme={NEW_THEME} shadow={NEW_SHADOW}"
    r = subprocess.run(["git", "commit", "-m", msg], cwd=REPO, capture_output=True, text=True)
    print(f"[git] committed: {msg}")

# Stash oauth + pull + push + pop
subprocess.run(["git", "stash", "push", "-m", "oauth-tmp", "--", ".oauth_cache/"],
               cwd=REPO, capture_output=True, text=True)
r = subprocess.run(["git", "pull", "--rebase"], cwd=REPO, capture_output=True, text=True)
print(f"[pull] rc={r.returncode} {r.stdout[:100]}")
r = subprocess.run(["git", "push"], cwd=REPO, capture_output=True, text=True)
print(f"[push] rc={r.returncode} {r.stdout[:100]}")
subprocess.run(["git", "stash", "pop"], cwd=REPO, capture_output=True, text=True)

# 4. Wait for workflow
print(f"\n[wait] Waiting for workflow (max 2min)...")
for i in range(12):
    time.sleep(10)
    r = subprocess.run(["gh", "run", "list", "--workflow=build-public.yml", "--limit", "1"],
                       capture_output=True, text=True)
    line = r.stdout.splitlines()[0] if r.stdout else ""
    print(f"  [{i*10:3d}s] {line[:140]}")
    if "completed" in line and ("success" in line or "failure" in line):
        break

# 5. Verify GH Pages
print(f"\n[verify] GH Pages after deploy...")
time.sleep(3)
try:
    with urllib.request.urlopen(GH_PAGES_URL, timeout=15) as r:
        html = r.read().decode("utf-8")
    idx = html.find("PUBLIC_ADMIN_THEME")
    if idx >= 0:
        snippet = html[idx:idx+500]
        import re
        m = re.search(r'"theme":\s*"([^"]+)"', snippet)
        remote_theme = m.group(1) if m else "?"
        m2 = re.search(r'"shadowTheme":\s*"([^"]+)"', snippet)
        remote_shadow = m2.group(1) if m2 else "?"
        print(f"  GH Pages theme       = {remote_theme}")
        print(f"  GH Pages shadowTheme = {remote_shadow}")
        if remote_theme == NEW_THEME:
            print(f"\n[SUCCESS] GH Pages has been updated to theme={NEW_THEME}")
        else:
            print(f"\n[INFO] Expected {NEW_THEME}, got {remote_theme}")
            print("        workflow may still be running or bake failed")
except Exception as e:
    print(f"  ERR: {e}")
