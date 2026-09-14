"""
repo_discovery.py — Tìm các repo GitHub của user có file repo.json.

Thuật toán:
  1. GET /users/{login}/repos?per_page=100&type=owner&sort=updated
     - Lấy tối đa 100 repo gần nhất (admin thường không có > 100 repo).
     - Filter `type=owner` (loại fork) vì fork có thể có repo.json nhưng
       admin thật là owner gốc — không cho phép edit qua repo của fork.
     - Filter `archived=false` (skip repo đã archive, không còn maintain).
     - Sort `updated` (ưu tiên repo active).
  2. Với mỗi repo candidate, thử GET contents ở NHIỀU path:
       - /repo.json (root — phổ biến nhất)
       - /.3105/repo.json (subpath ẩn, cho repo có convention dot-prefix)
       - /config/repo.json
       - /src/repo.json
     → Repo đầu tiên có file hợp lệ → đánh dấu candidate.
  3. Parse file → Schema:
       {
         "slug": str,             # required, vd "my-cool-repo"
         "identifier": str,       # required, vd "com.user.repo"
         "name": str,
         "owner_github": str,      # login GitHub của admin
         "created_at": str,       # ISO 8601
       }
     Nếu thiếu field required → skip (không phải repo.json hợp lệ).
  4. Trả về list[RepoCandidate] đã sort theo updated_at desc.

Rate limit:
  - User token: 5000/h → scan 100 repos × 4 paths = 400 calls. OK.
  - Cache TTL: 5 phút (Config.REPO_DISCOVERY_CACHE_TTL).
  - Có thể scan 1000+ repos nếu cần bằng pagination (?page=2&per_page=100).
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, asdict
from typing import Any

import requests
from flask import current_app


# Path candidates để tìm repo.json — thứ tự ưu tiên giảm dần.
#
# Mục đích: cho phép admin tự do cấu trúc repo, đặc biệt:
#  - Standard fork: repo.json ở root
#  - YangJii 3105 fork: 3105-repo/repositories/demo/repo.json (theo format cũ)
#  - Hidden: .3105/repo.json
#  - Subpath: config/ hoặc src/
#
# LƯU Ý QUAN TRỌNG:
#  - GitHub Contents API yêu cầu exact path. Nếu path sai → 404.
#  - Thứ tự ưu tiên: path nào phổ biến nhất → check trước (tiết kiệm rate).
#  - Mỗi path được cache 1 lần — nếu path đầu fail, không cache fail (check path sau).
#
REPO_JSON_PATHS: tuple[str, ...] = (
    # === Standard (phổ biến nhất) ===
    "repo.json",
    ".3105/repo.json",

    # === YangJii/3105 fork (legacy structure) ===
    # Repo gốc của YangJii: https://github.com/YangJii/3105
    # Admin thường fork về và fork có cấu trúc: 3105-repo/repositories/demo/...
    "3105-repo/repositories/demo/repo.json",
    "3105-repo/repositories/demo/repo.yml",
    "repositories/demo/repo.json",
    "repositories/demo/repo.yml",

    # === Config / source subpaths ===
    "config/repo.json",
    "src/repo.json",
    "docs/repo.json",

    # === Old variants ===
    "repo.yml",
    "repository.json",
)


@dataclass
class RepoCandidate:
    """Metadata của repo mà user là admin."""
    slug: str                       # required, dùng để identify repo
    identifier: str                 # required, vd "com.user.repo"
    name: str | None
    owner_github: str
    full_name: str                  # "owner/repo" — dùng cho GitHub API path
    html_url: str                   # link GitHub repo
    description: str | None         # mô tả repo
    default_branch: str             # branch mặc định
    updated_at: str                 # ISO 8601
    repo_json_path: str             # path nào đã tìm thấy file repo.json
    private: bool
    releases: list[dict]            # GitHub Releases mapping package_id → download_url
    download_paths: list[dict]      # raw file .3105 mapping package_id → raw_url
    download_mode: str              # "raw" | "releases" | "auto"

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ("releases", "download_paths", "download_mode")}


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def scan_user_repos(token: str, login: str) -> list[dict[str, Any]]:
    """Trả về list RepoCandidate (as dict) của user.

    Quy trình:
      1. List repos của user (pagination, max ~1000).
      2. Với mỗi repo, check repo.json ở các path candidates.
      3. Parse + validate.
      4. Sort theo updated_at desc.
    """
    repos = _list_user_repos(token, login)
    candidates: list[RepoCandidate] = []
    for repo in repos:
        candidate = _try_discover_repo_json(token, repo)
        if candidate is not None:
            candidates.append(candidate)
    # Sort theo updated_at desc (gần nhất trước)
    candidates.sort(key=lambda r: r.updated_at, reverse=True)
    return [c.to_dict() for c in candidates]


# -----------------------------------------------------------------------------
# Internal
# -----------------------------------------------------------------------------

def _list_user_repos(token: str, login: str) -> list[dict[str, Any]]:
    """GET /users/{login}/repos — pagination, filter owner-only + non-archived."""
    repos: list[dict[str, Any]] = []
    page = 1
    headers = _gh_headers(token)

    while page <= 10:  # safety cap: 10 pages × 100 = 1000 repos
        url = f"https://api.github.com/users/{login}/repos"
        params = {
            "type": "owner",         # skip forks
            "sort": "updated",
            "per_page": 100,
            "page": page,
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
        except requests.RequestException as e:
            current_app.logger.warning(f"github list_repos page {page} failed: {e}")
            break

        if resp.status_code == 403:
            # Rate limited
            current_app.logger.warning(f"github rate-limited at page {page}")
            break
        if resp.status_code != 200:
            current_app.logger.warning(f"github list_repos status {resp.status_code}: {resp.text[:200]}")
            break

        batch = resp.json()
        if not isinstance(batch, list) or len(batch) == 0:
            break

        for r in batch:
            # Skip archived (không còn maintain), skip forks (đã có type=owner
            # nhưng check lại cho chắc)
            if r.get("archived"):
                continue
            if r.get("fork"):
                continue
            repos.append(r)

        if len(batch) < 100:
            break  # hết page
        page += 1

    return repos


def _try_discover_repo_json(token: str, repo: dict[str, Any]) -> RepoCandidate | None:
    """Thử tìm repo.json trong 1 repo (full_name = owner/repo)."""
    full_name = repo.get("full_name")
    if not full_name:
        return None

    for path in REPO_JSON_PATHS:
        try:
            content, sha = _get_file_contents(token, full_name, path)
        except FileNotFoundError:
            continue
        except requests.RequestException as e:
            current_app.logger.debug(f"github get {full_name}/{path} failed: {e}")
            continue

        # Parse + validate
        parsed = _parse_and_validate_repo_json(content)
        if parsed is None:
            continue

        return RepoCandidate(
            slug=parsed["slug"],
            identifier=parsed["identifier"],
            name=parsed.get("name") or repo.get("name"),
            owner_github=parsed.get("owner_github") or repo.get("owner", {}).get("login", ""),
            full_name=full_name,
            html_url=repo.get("html_url", ""),
            description=repo.get("description"),
            default_branch=repo.get("default_branch", "main"),
            updated_at=repo.get("updated_at", ""),
            repo_json_path=path,
            private=repo.get("private", False),
            releases=parsed.get("releases", []),
            download_paths=parsed.get("download_paths", []),
            download_mode=parsed.get("download_mode", "auto"),
        )

    return None


def _get_file_contents(token: str, full_name: str, path: str) -> tuple[dict, str]:
    """GET /repos/{owner}/{repo}/contents/{path} → (parsed dict, sha).

    Supports cả `.json` và `.yml` (auto-detect theo extension).

    Raises:
      FileNotFoundError: 404 (path không tồn tại)
      requests.RequestException: network errors
      ValueError: content không parse được
    """
    url = f"https://api.github.com/repos/{full_name}/contents/{path}"
    resp = requests.get(url, headers=_gh_headers(token), timeout=10)
    if resp.status_code == 404:
        raise FileNotFoundError(f"{full_name}/{path}")
    resp.raise_for_status()
    data = resp.json()
    # GitHub trả content base64-encoded. Decode để parse.
    encoded = data.get("content", "")
    if not encoded:
        raise FileNotFoundError(f"{full_name}/{path} empty")
    try:
        raw = base64.b64decode(encoded).decode("utf-8")
        # Auto-detect: .yml/.yaml → YAML, .json → JSON
        if path.endswith((".yml", ".yaml")):
            import yaml  # PyYAML (đã có trong requirements)
            parsed = yaml.safe_load(raw)
        else:
            parsed = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as e:
        raise ValueError(f"{full_name}/{path} not parseable: {e}")
    return parsed, data.get("sha", "")


def _parse_and_validate_repo_json(raw: dict) -> dict | None:
    """Validate schema. Trả về dict normalized hoặc None nếu invalid.

    Schema:
      {
        "slug": str,               # required
        "identifier": str,         # required
        "name": str,               # optional
        "owner_github": str,       # optional
        "releases": [              # optional — GitHub Releases cho packages
          {
            "package_id": str,
            "version": str,
            "tag": str,
            "asset_name": str,
            "download_url": str,    # URL release (browser_download_url)
            "size_bytes": int,
            "sha256": str,
          },
          ...
        ],
        "download_paths": [        # optional — override raw URL cho file .3105
          {
            "package_id": str,
            "path": str,           # exact path trong repo
            "raw_url": str,        # full URL raw.githubusercontent.com
            "asset_name": str,     # filename
            "size_bytes": int,
            "sha": str,            # git blob sha
          },
          ...
        ],
        "download_mode": str,      # optional — "raw" | "releases" | "auto" (default "auto")
      }
    """
    if not isinstance(raw, dict):
        return None
    slug = raw.get("slug")
    identifier = raw.get("identifier")
    if not isinstance(slug, str) or not slug.strip():
        return None
    if not isinstance(identifier, str) or not identifier.strip():
        return None

    # Validate releases[]
    releases = raw.get("releases", [])
    if not isinstance(releases, list):
        releases = []
    else:
        valid_releases = []
        for r in releases:
            if not isinstance(r, dict):
                continue
            pkg_id = r.get("package_id")
            dl = r.get("download_url")
            if not isinstance(pkg_id, str) or not isinstance(dl, str):
                continue
            valid_releases.append({
                "package_id": pkg_id,
                "version": r.get("version", ""),
                "tag": r.get("tag", ""),
                "asset_name": r.get("asset_name", ""),
                "download_url": dl,
                "size_bytes": int(r.get("size_bytes", 0)),
                "sha256": r.get("sha256", ""),
            })
        releases = valid_releases

    # Validate download_paths[]
    download_paths = raw.get("download_paths", [])
    if not isinstance(download_paths, list):
        download_paths = []
    else:
        valid_paths = []
        for dp in download_paths:
            if not isinstance(dp, dict):
                continue
            pkg_id = dp.get("package_id")
            raw_url = dp.get("raw_url")
            if not isinstance(pkg_id, str) or not isinstance(raw_url, str):
                continue
            valid_paths.append({
                "package_id": pkg_id,
                "path": dp.get("path", ""),
                "raw_url": raw_url,
                "asset_name": dp.get("asset_name", ""),
                "size_bytes": int(dp.get("size_bytes", 0)),
                "sha": dp.get("sha", ""),
            })
        download_paths = valid_paths

    # Validate download_mode
    download_mode = raw.get("download_mode", "auto")
    if download_mode not in ("raw", "releases", "auto"):
        download_mode = "auto"

    return {
        "slug": slug.strip(),
        "identifier": identifier.strip(),
        "name": raw.get("name"),
        "owner_github": raw.get("owner_github"),
        "releases": releases,
        "download_paths": download_paths,
        "download_mode": download_mode,
    }


def _gh_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "3105-repo-builder/1.0",
    }
