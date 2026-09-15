"""
github_raw.py — Resolve download URL cho `.3105` file từ GitHub repo.

Strategy (cho Front Repo của user thường, không cần login):
  1. Override: repo.json.download_paths[].raw_url cho package_id cụ thể
  2. Auto-detect: scan folder packages/ trong repo qua GitHub Contents API
     - Convention 1: `packages/{package_id}.3105`
     - Convention 2: `packages/{package_id}/{any}.3105`
     - Convention 3: `packages/{package_id}-{version}.3105`
  3. Fallback: GitHub Releases API (đã có trong github_release.py)

Áp dụng cho repo fork YangJii/3105:
  - Repo structure: `3105-repo/repositories/demo/packages/{file}.3105`
  - Có thể đổi tên 3105-repo thành bất kỳ → cần query owner_github để build URL

raw URL format: https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}
GitHub Contents API: GET /repos/{o}/{r}/contents/{path} → list hoặc file metadata
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote

import requests
from flask import current_app, jsonify

from .config import Config


# Path candidates cho folder chứa packages (theo convention fork YangJii/3105)
PACKAGES_DIR_CANDIDATES = (
    # === YangJii/3105 fork structure ===
    "3105-repo/repositories/demo/packages",
    "3105-repo/repositories/{slug}/packages",
    "repositories/demo/packages",
    "repositories/{slug}/packages",

    # === Other common layouts ===
    "packages",
    "dist",
    "build/packages",
    "src/packages",

    # === Hidden ===
    ".3105/packages",
)


def build_raw_url(owner: str, repo: str, branch: str, file_path: str) -> str:
    """Build raw.githubusercontent.com URL.

    Args:
      owner: GitHub username
      repo: repo name
      branch: branch name (main / master / etc.)
      file_path: path tới file trong repo
    """
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path.lstrip('/')}"


def _get_default_branch(token: str | None, owner: str, repo: str) -> str:
    """Fetch default branch của repo. Nếu fail → 'main'."""
    url = f"{Config.GITHUB_API_BASE}/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "3105-repo-builder/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif Config.GITHUB_PAT:
        # Use server PAT cho public reads (rate limit)
        headers["Authorization"] = f"Bearer {Config.GITHUB_PAT}"
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("default_branch", "main")
    except requests.RequestException:
        pass
    return "main"


def _list_contents(token: str | None, owner: str, repo: str, path: str) -> list[dict]:
    """GET /repos/{o}/{r}/contents/{path} → list entries (nếu path là folder)."""
    url = f"{Config.GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "3105-repo-builder/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif Config.GITHUB_PAT:
        headers["Authorization"] = f"Bearer {Config.GITHUB_PAT}"
    try:
        resp = requests.get(url, headers=headers, params={"ref": "HEAD"}, timeout=10)
        if resp.status_code == 404:
            return []
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, dict):
            # Single file (không phải folder)
            return [data]
        return data or []
    except requests.RequestException:
        return []


def find_packages_in_repo(
    owner: str,
    repo: str,
    slug: str = "demo",
    *,
    token: str | None = None,
    package_ids: list[str] | None = None,
    download_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Scan repo, tìm file `.3105` cho mỗi package_id.

    Returns: {package_id: raw_url}

    Logic:
      - Thử PACKAGES_DIR_CANDIDATES lần lượt
      - Với mỗi folder tồn tại, list contents → tìm file match package_id
      - Match strategies:
        a) Exact: `{package_id}.3105`
        b) Versioned: `{package_id}-{version}.3105`
        c) Folder: `{package_id}/latest.3105` hoặc `{package_id}/any.3105`
        d) Reverse lookup (download_map): {filename: package_id} - nếu file
           trong folder packages/ tên là "PATCH_FREE_V2_GLOBAL.3105" nhưng
           package_id là "owen-003", dùng download_map từ repo.json để map.
    """
    if not owner or not repo:
        return {}

    branch = _get_default_branch(token, owner, repo)
    found: dict[str, str] = {}
    # Reverse map: filename → package_id (lowercase basename)
    rev_map: dict[str, str] = {}
    if download_map:
        for pkg_id, dl_path in download_map.items():
            if not dl_path:
                continue
            base = dl_path.replace("\\", "/").split("/")[-1].lower()
            if base:
                rev_map[base] = pkg_id

    # Thử từng path candidate
    for dir_template in PACKAGES_DIR_CANDIDATES:
        dir_path = dir_template.format(slug=slug)
        entries = _list_contents(token, owner, repo, dir_path)
        if not entries:
            continue

        if package_ids:
            # Filter chỉ entries match package_ids
            for pkg_id in package_ids:
                if pkg_id in found:
                    continue  # Đã tìm thấy ở path trước rồi
                # Strategy A: Nếu có download_map, tìm filename basename
                # tương ứng với package_id này rồi match exact.
                target_basename = None
                if download_map:
                    dl = download_map.get(pkg_id, "")
                    if dl:
                        target_basename = dl.replace("\\", "/").split("/")[-1]
                for entry in entries:
                    name = entry.get("name", "")
                    if not name.endswith(".3105"):
                        continue
                    # 1) Exact match basename từ download_map
                    if target_basename and name.lower() == target_basename.lower():
                        file_path = f"{dir_path}/{name}".replace("//", "/")
                        found[pkg_id] = build_raw_url(owner, repo, branch, file_path)
                        break
                    # 2) Fallback: convention-based match
                    if _match_package_entry(pkg_id, name):
                        file_path = f"{dir_path}/{name}".replace("//", "/")
                        found[pkg_id] = build_raw_url(owner, repo, branch, file_path)
                        break
        else:
            # No filter: map mọi file .3105 theo convention
            for entry in entries:
                name = entry.get("name", "")
                if not name.endswith(".3105"):
                    continue
                # Prefer rev_map (download_map từ repo.json)
                pkg_id = rev_map.get(name.lower())
                if not pkg_id:
                    pkg_id = _extract_package_id(name)
                if pkg_id and pkg_id not in found:
                    file_path = f"{dir_path}/{name}".replace("//", "/")
                    found[pkg_id] = build_raw_url(owner, repo, branch, file_path)

        if found and package_ids and all(p in found for p in package_ids):
            break  # Tìm đủ

    return found


def _match_package_entry(package_id: str, filename: str) -> bool:
    """Match filename với package_id.

    Strategies:
      a) {package_id}.3105
      b) {package_id}-v1.2.0.3105
      c) {package_id}-1.2.0.3105
      d) starts-with: {package_id} (cho folder {package_id}/... case đã được handle riêng)
    """
    name_no_ext = filename[:-len(".3105")]
    # Exact
    if name_no_ext == package_id:
        return True
    # Versioned: split by '-' lần cuối nếu là semver
    if "-" in name_no_ext:
        # Tìm phần version (vd -1.2.0 hoặc -v1.2.0)
        m = re.match(r"^(.+)-v?\d+\.\d+\.\d+(?:[-+].+)?$", name_no_ext)
        if m and m.group(1) == package_id:
            return True
        # Hoặc starts-with
        if name_no_ext.startswith(package_id + "-") or name_no_ext.startswith(package_id):
            return True
    return False


def _extract_package_id(filename: str) -> str | None:
    """Từ filename .3105, suy ra package_id."""
    if not filename.endswith(".3105"):
        return None
    name = filename[:-len(".3105")]
    if "-" in name:
        m = re.match(r"^(.+)-v?\d+\.\d+\.\d+(?:[-+].+)?$", name)
        if m:
            return m.group(1)
        return name  # Fallback
    return name


# ---------------------------------------------------------------------------
# Route (public, không cần auth)
# ---------------------------------------------------------------------------

def register_raw_routes(app):
    """Đăng ký routes cho raw asset resolution."""

    @app.get("/api/public/raw-asset/<owner>/<repo>/<slug>/<path:package_id>")
    def api_public_raw_asset(owner: str, repo: str, slug: str, package_id: str):
        """Resolve raw URL cho file .3105 của package.

        Args:
          owner: GitHub username
          repo: repo name
          slug: repo slug (vd "demo")
          package_id: vd "com.example.pkg1"

        Returns: {
          "ok": True,
          "download_url": "https://raw.githubusercontent.com/.../file.3105",
          "source": "repo_json | auto_detect",
          "size_bytes": 12345,
          "sha": "abc...",
        }
        """
        import time as _time

        cache_key = f"raw_asset:{owner}:{repo}:{slug}:{package_id}"
        cached = app.config.get(cache_key)
        cache_ts = app.config.get(cache_key + ":ts", 0)
        now = _time.time()
        if cached is not None and (now - cache_ts) < 300:
            return jsonify(cached)

        # 1. Override: repo.json.download_paths[].raw_url
        try:
            from .repo_discovery import REPO_JSON_PATHS
            full_name = f"{owner}/{repo}"
            for path in REPO_JSON_PATHS:
                from .repo_discovery import _get_file_contents
                try:
                    content, _ = _get_file_contents(None, full_name, path)
                except FileNotFoundError:
                    continue
                if not isinstance(content, dict):
                    continue
                # Ưu tiên: download_paths[].package_id match → raw_url
                for dp in content.get("download_paths", []):
                    if dp.get("package_id") == package_id and dp.get("raw_url"):
                        result = {
                            "ok": True,
                            "download_url": dp["raw_url"],
                            "source": "repo_json",
                            "size_bytes": dp.get("size_bytes", 0),
                            "sha": dp.get("sha", ""),
                            "asset_name": dp.get("asset_name", ""),
                            "path": dp.get("path", ""),
                        }
                        app.config[cache_key] = result
                        app.config[cache_key + ":ts"] = now
                        return jsonify(result)

                # Build download_map từ packages[] trong repo.json:
                # {package_id: download_field_basename}
                # Đây là cách fork YangJii/3105 hoạt động: file .3105 có tên
                # khác với identifier (vd "PATCH_FREE_V2_GLOBAL.3105" cho
                # package_id="owen-003"), nhưng repo.json ghi rõ trong field
                # "download": "packages/PATCH_FREE_V2_GLOBAL.3105".
                download_map: dict[str, str] = {}
                for pkg in content.get("packages", []):
                    pid = pkg.get("identifier")
                    dl = pkg.get("download") or ""
                    if pid and dl:
                        download_map[pid] = dl

                # Tìm package này trong folder packages/ qua reverse-mapping
                # từ repo.json (KHÔNG cần dựa vào filename convention).
                found = find_packages_in_repo(
                    owner, repo, slug,
                    token=None,
                    package_ids=[package_id],
                    download_map=download_map,
                )
                if found.get(package_id):
                    url = found[package_id]
                    # Try to get file size/sha
                    size, sha = _head_file_size_sha(None, owner, repo, _path_from_raw_url(url))
                    result = {
                        "ok": True,
                        "download_url": url,
                        "source": "auto_detect_with_repo_json",
                        "size_bytes": size,
                        "sha": sha,
                    }
                    app.config[cache_key] = result
                    app.config[cache_key + ":ts"] = now
                    return jsonify(result)

            # Không có repo.json nào khớp → fallback scan toàn repo
            found = find_packages_in_repo(
                owner, repo, slug, token=None, package_ids=[package_id])
            if found.get(package_id):
                url = found[package_id]
                size, sha = _head_file_size_sha(None, owner, repo, _path_from_raw_url(url))
                result = {
                    "ok": True,
                    "download_url": url,
                    "source": "auto_detect",
                    "size_bytes": size,
                    "sha": sha,
                }
                app.config[cache_key] = result
                app.config[cache_key + ":ts"] = now
                return jsonify(result)

        except Exception as e:
            current_app.logger.warning(f"raw-asset lookup failed: {e}")

        return jsonify({
            "ok": False,
            "error": f"Không tìm thấy file .3105 cho {package_id} trong {owner}/{repo}",
        }), 404


def _path_from_raw_url(raw_url: str) -> str:
    """raw.githubusercontent.com/{o}/{r}/{branch}/{path} → {path}."""
    parts = raw_url.replace("https://raw.githubusercontent.com/", "").split("/", 3)
    if len(parts) >= 4:
        return parts[3]
    return ""


def _head_file_size_sha(token: str | None, owner: str, repo: str, path: str) -> tuple[int, str]:
    """Get file size + sha qua Contents API (HEAD-like)."""
    url = f"{Config.GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "3105-repo-builder/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("size", 0), data.get("sha", "")
    except requests.RequestException:
        pass
        return 0, ""
