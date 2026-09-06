"""Script one-shot: regenerate repo.yml từ repo.json hiện tại, bỏ key lạ ở root."""
import json
import yaml

DATA_FILE = r"C:\Users\NK\Desktop\MOD\3105-repo\repositories\demo\repo.json"
OUT_FILE = r"C:\Users\NK\Desktop\MOD\3105-repo\repositories\demo\repo.yml"

with open(DATA_FILE, encoding="utf-8") as f:
    data = json.load(f)

# Loại bỏ 2 key lạ ở root (do anchor YAML cũ sinh ra)
for k in ["shared_os", "shared_screens"]:
    data.pop(k, None)


def _q(v):
    """Quote string nếu cần."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, str):
        if any(c in v for c in [":", "#", "&", "*", "!", "|", ">", "%", "@", "`", '"', "'", "\n"]):
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return v
    return str(v)


lines = []
lines.append("# ==========================================")
lines.append("# THÔNG TIN CHUNG CỦA REPO")
lines.append("# ==========================================")
lines.append("")

for key in ("schemaVersion", "identifier", "name", "accentColor"):
    if key in data:
        lines.append(f"{key}: {_q(data[key])}")

if "description" in data:
    lines.append(f"description: {_q(data['description'])}")
if "icon" in data:
    lines.append(f"icon: {data['icon']}")
lines.append("")

lines.append("# ==========================================")
lines.append("# DANH SÁCH PACKAGES")
lines.append("# ==========================================")
lines.append("")
lines.append("packages:")

for pkg in data.get("packages") or []:
    ident = pkg.get("identifier", "unknown")
    lines.append(f"  # ----- {ident} -----")
    lines.append(f"  - identifier: {_q(pkg.get('identifier', ''))}")
    lines.append(f"    name: {_q(pkg.get('name', ''))}")
    if pkg.get("author"):
        lines.append(f"    author: {_q(pkg['author'])}")
    if pkg.get("version"):
        lines.append(f"    version: {_q(str(pkg['version']))}")
    if pkg.get("summary"):
        lines.append(f"    summary: {_q(pkg['summary'])}")
    if pkg.get("password") is not None:
        lines.append(f'    password: "{pkg["password"]}"')
    if pkg.get("category"):
        lines.append(f"    category: {_q(pkg['category'])}")
    if pkg.get("tags"):
        lines.append(f"    tags: [{', '.join(str(t) for t in pkg['tags'])}]")
    if pkg.get("publishedAt"):
        lines.append(f"    publishedAt: {_q(pkg['publishedAt'])}")
    if pkg.get("kind"):
        lines.append(f"    kind: {_q(pkg['kind'])}")
    if pkg.get("icon"):
        lines.append(f"    icon: {pkg['icon']}")
    if pkg.get("banner"):
        lines.append(f"    banner: {pkg['banner']}")

    if pkg.get("screenshots"):
        lines.append("    screenshots:")
        for s in pkg["screenshots"]:
            lines.append(f"      - {s}")

    if pkg.get("download"):
        lines.append(f"    download: {pkg['download']}")
    if pkg.get("sha256"):
        lines.append(f"    sha256: {pkg['sha256']}")
    if pkg.get("size") is not None:
        lines.append(f"    size: {pkg['size']}")

    if pkg.get("supportedOS"):
        lines.append("    supportedOS:")
        for rule in pkg["supportedOS"]:
            lines.append(f"      - minimum: \"{rule['minimum']}\"")
            lines.append(f"        maximum: \"{rule['maximum']}\"")
            if rule.get("builds"):
                lines.append(f"        builds: {json.dumps(rule['builds'], ensure_ascii=False)}")

    lines.append(f"    featured: {str(bool(pkg.get('featured', False))).lower()}")
    lines.append(f"    isPrivate: {str(bool(pkg.get('isPrivate', False))).lower()}")

    if pkg.get("description"):
        lines.append("    description: |")
        for ln in str(pkg["description"]).splitlines():
            lines.append(f"      {ln}")

    if pkg.get("changelog"):
        lines.append("    changelog: |")
        for ln in str(pkg["changelog"]).splitlines():
            lines.append(f"      {ln}")
    lines.append("")

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines).rstrip() + "\n")

# Verify
with open(OUT_FILE, encoding="utf-8") as f:
    d2 = yaml.safe_load(f)
print("DONE")
print("Top-level keys:", list(d2.keys()))
print("Packages:", len(d2.get("packages") or []))
