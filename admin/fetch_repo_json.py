"""
fetch_repo_json.py — Helper để fetch repo.json từ GitHub (client-side, public API).
Dùng trong template JS để lấy download_paths từ repo.json mà không cần auth token.
"""
from __future__ import annotations

import re
from typing import Any
from flask import Blueprint, jsonify

from .config import Config

fetch_bp = Blueprint("fetch_repo_json", __name__)


# Path candidates — giống trong repo_discovery.py
REPO_JSON_PATHS = (
    "repo.json",
    ".3105/repo.json",
    "3105-repo/repositories/demo/repo.json",
    "3105-repo/repositories/demo/repo.yml",
    "repositories/demo/repo.json",
    "repositories/demo/repo.yml",
    "config/repo.json",
    "src/repo.json",
    "docs/repo.json",
    "repo.yml",
    "repository.json",
)


@fetch_bp.route("/api/fetch-repo-json/<owner>/<repo>/<slug>")
def api_fetch_repo_json(owner: str, repo: str, slug: str):
    """Fetch repo.json từ GitHub + extract download info cho mỗi package.

    Dùng cho: Front Repo anonymous user → lấy download URLs mà không cần auth.
    - Thử tất cả path candidates
    - Parse packages[] → map identifier → download path
    - Resolve relative path → raw URL
    """
    import time as _time
    import requests as _req
    import base64 as _b64
    import json as _json

    cache_key = f"fetch_repo_json:{owner}:{repo}:{slug}"
    cached = app.config.get(cache_key)
    cache_ts = app.config.get(cache_key + ":ts", 0)
    now = _time.time()
    if cached is not None and (now - cache_ts) < 300:
        return jsonify(cached)

    full_name = f"{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "3105-repo-builder/1.0",
    }
    # Use PAT for read requests to bypass 60/hr rate limit.
    if Config.GITHUB_PAT:
        headers["Authorization"] = f"Bearer {Config.GITHUB_PAT}"

    # Get default branch
    branch = "main"
    try:
        url = f"{Config.GITHUB_API_BASE}/repos/{full_name}"
        resp = _req.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            branch = resp.json().get("default_branch", "main")
    except _req.RequestException:
        pass

    repo_json_data = None
    repo_json_path = None

    for path in REPO_JSON_PATHS:
        url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/contents/{path}"
        try:
            resp = _req.get(url, headers=headers, params={"ref": branch}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                raw = _b64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
                if path.endswith((".yml", ".yaml")):
                    import yaml as _y
                    repo_json_data = _y.safe_load(raw)
                else:
                    repo_json_data = _json.loads(raw)
                repo_json_path = path
                break
            # 403 = rate limit / 404 = not found → both treated as "không tìm thấy"
            # để user có thể tiếp tục dùng (vd: manual upload).
            if resp.status_code in (403, 404):
                continue
        except (_req.RequestException, _json.JSONDecodeError, _b64.binascii.Error):
            continue

    if not repo_json_data or not isinstance(repo_json_data, dict):
        result = {
            "ok": False,
            "error": f"Không tìm thấy repo.json trong {full_name}",
            "packages": [],
            "download_paths": [],
        }
        app.config[cache_key] = result
        app.config[cache_key + ":ts"] = now
        return jsonify(result), 404

    # Build download paths từ packages[]
    packages_list = repo_json_data.get("packages") or []
    download_paths = []
    download_mode = repo_json_data.get("download_mode", "auto")

    for pkg in packages_list:
        if not isinstance(pkg, dict):
            continue
        identifier = pkg.get("identifier")
        if not identifier:
            continue

        # "download" field: relative path trong repo (vd "packages/PATCH_FREE_V2_VNG.3105")
        download_rel = pkg.get("download")
        if download_rel:
            # Resolve relative path → raw URL
            raw_url = (
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/"
                f"{download_rel.lstrip('/')}"
            )
            download_paths.append({
                "package_id": identifier,
                "path": download_rel,
                "raw_url": raw_url,
                "asset_name": download_rel.split("/")[-1] if "/" in download_rel else download_rel,
                "size_bytes": 0,  # không fetch metadata để tiết kiệm request
                "sha": "",
            })

    # Also include explicit download_paths from repo.json (admin override)
    for dp in repo_json_data.get("download_paths") or []:
        if isinstance(dp, dict) and dp.get("package_id") and dp.get("raw_url"):
            download_paths.append(dp)

    # Merge: explicit download_paths override auto-detect
    dp_map = {}
    for dp in download_paths:
        pkg_id = dp.get("package_id")
        if pkg_id:
            dp_map[pkg_id] = dp
    download_paths = list(dp_map.values())

    result = {
        "ok": True,
        "owner_github": owner,
        "repo": repo,
        "slug": slug,
        "branch": branch,
        "repo_json_path": repo_json_path,
        "download_mode": download_mode,
        "download_paths": download_paths,
        "releases": repo_json_data.get("releases") or [],
        "packages_count": len(packages_list),
    }
    app.config[cache_key] = result
    app.config[cache_key + ":ts"] = now
    return jsonify(result)


# Reference app for config cache — set by register_blueprint
app = None


def register_fetch_repo_json(flask_app):
    global app
    app = flask_app
    flask_app.register_blueprint(fetch_bp)
