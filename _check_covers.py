"""Inspect cover URLs in admin playlist."""
import json
import re

d = json.load(open(r"C:\Users\NK\Desktop\MOD\3105-repo\.3105\admin-settings.json", encoding="utf-8"))
raw = d.get("admin_playlist", "")
covers = re.findall(r'"cover":"([^"]+)"', raw)
print(f"Found {len(covers)} cover URLs:")
for c in covers:
    print(f"  {c}")
