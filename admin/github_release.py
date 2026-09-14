"""
github_release.py — Tạo GitHub Release + upload asset (.3105 binary).

GitHub Releases API:
  POST /repos/{owner}/{repo}/releases
    {
      "tag_name": "v1.2.0",
      "target_commitish": "main",  # branch
      "name": "Release v1.2.0",
      "body": "Release notes...",
      "draft": false,
      "prerelease": false,
    }
  → {id, html_url, upload_url, ...}

Upload asset:
  POST {upload_url}  (thay {?name,label} placeholder bằng tên file)
  Headers: Content-Type, Authorization
  Body: binary content

Flow:
  1. Tạo release (nếu tag chưa tồn tại) hoặc lấy release hiện có
  2. Upload file .3105 lên release đó
  3. Trả về download_url (browser-friendly)
     - Native: https://github.com/{o}/{r}/releases/download/{tag}/{file}
     - Direct redirect: https://github.com/{o}/{r}/releases/expanded_assets/{tag}/{file}

Sau khi release xong, admin cần update `repo.json` để thêm release URL vào
mảng `releases[]` (mapping package_id → download_url).
"""
from __future__ import annotations

import hashlib
import mimetypes
import re
import urllib.parse
from typing import Any

import requests
from flask import current_app

from .config import Config


def _gh_headers(token: str, *, json_body: bool = True) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "3105-repo-builder/1.0",
    }
    if json_body:
        h["Content-Type"] = "application/json"
    return h


_TAG_RE = re.compile(r"^v?\d+\.\d+\.\d+(?:[-+].+)?$")  # v1.2.0, 1.2.0, 1.2.0-rc1


def _validate_tag(tag: str) -> str | None:
    if not isinstance(tag, str) or not tag.strip():
        return "Thiếu tag_name"
    if not _TAG_RE.match(tag.strip()):
        return f"tag không hợp lệ: {tag!r} (expected semver vd 'v1.2.0' hoặc '1.2.0')"
    return None


def _validate_filename(name: str) -> str | None:
    """Tên asset không chứa / hay .., không quá dài."""
    if not isinstance(name, str) or not name.strip():
        return "Thiếu asset name"
    if "/" in name or "\\" in name or ".." in name:
        return f"asset name không hợp lệ: {name!r}"
    if len(name) > 200:
        return "asset name quá dài"
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_or_get_release(
    token: str,
    full_name: str,
    tag_name: str,
    *,
    target_branch: str = "main",
    name: str | None = None,
    body: str = "",
    draft: bool = False,
    prerelease: bool = False,
) -> dict[str, Any]:
    """Tạo release mới (hoặc lấy release hiện có nếu tag đã tồn tại).

    Returns: {id, html_url, upload_url, tag_name, ...}
    """
    err = _validate_tag(tag_name)
    if err:
        raise ValueError(err)

    # Thử lấy release hiện có
    existing = _get_release_by_tag(token, full_name, tag_name)
    if existing:
        return existing

    # Tạo mới
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/releases"
    payload = {
        "tag_name": tag_name.strip(),
        "target_commitish": target_branch,
        "name": name or f"Release {tag_name.strip()}",
        "body": body or f"Release {tag_name.strip()} via 3105 Builder.",
        "draft": draft,
        "prerelease": prerelease,
    }
    resp = requests.post(url, headers=_gh_headers(token), json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Tạo release thất bại: {resp.status_code} {resp.text[:300]}"
        )
    return resp.json()


def upload_release_asset(
    token: str,
    full_name: str,
    release_id: int,
    asset_name: str,
    asset_bytes: bytes,
    *,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Upload 1 asset (.3105 file) lên release.

    Returns: {
      "id": asset_id,
      "name": asset_name,
      "size": bytes,
      "browser_download_url": "https://github.com/.../releases/download/{tag}/{name}",
      "sha256": "..."
    }
    """
    err = _validate_filename(asset_name)
    if err:
        raise ValueError(err)

    # Lấy upload_url từ release hiện có
    release = _get_release_by_id(token, full_name, release_id)
    if not release:
        raise RuntimeError(f"Release id={release_id} không tồn tại")
    upload_url = release.get("upload_url", "")
    if not upload_url:
        raise RuntimeError("Release thiếu upload_url")

    # upload_url có format "...releases/{id}/assets{?name,label}"
    # Cần replace {?name,label} bằng ?name=...
    upload_endpoint = upload_url.split("{")[0]
    upload_endpoint += f"?name={urllib.parse.quote(asset_name)}"

    mime = content_type or mimetypes.guess_type(asset_name)[0] or "application/octet-stream"

    # SHA256 cho integrity check
    sha256 = hashlib.sha256(asset_bytes).hexdigest()

    # Upload KHÔNG set Content-Type: application/json (dùng binary)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "Content-Type": mime,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "3105-repo-builder/1.0",
    }
    resp = requests.post(
        upload_endpoint, headers=headers, data=asset_bytes, timeout=300,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Upload asset thất bại: {resp.status_code} {resp.text[:300]}"
        )
    data = resp.json()
    return {
        "id": data.get("id"),
        "name": data.get("name", asset_name),
        "size": data.get("size", len(asset_bytes)),
        "browser_download_url": data.get("browser_download_url", ""),
        "sha256": sha256,
        "state": data.get("state", "uploaded"),
    }


def list_releases(token: str, full_name: str, *, per_page: int = 30) -> list[dict[str, Any]]:
    """GET /repos/{o}/{r}/releases → list releases (mới nhất trước)."""
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/releases"
    params = {"per_page": per_page}
    try:
        resp = requests.get(
            url,
            headers={**_gh_headers(token, json_body=False), "Content-Type": ""},
            params=params,
            timeout=15,
        )
    except requests.RequestException as e:
        current_app.logger.warning(f"list_releases failed: {e}")
        return []
    if resp.status_code != 200:
        return []
    return resp.json() or []


def find_release_for_package(
    token: str, full_name: str, package_identifier: str,
) -> dict[str, Any] | None:
    """Tìm release có asset tên chứa package_identifier.

    Strategy: match by filename convention `{package_identifier}-{version}.3105`
    hoặc `pkg-{package_identifier}.3105`. Trả về asset dict đầu tiên match.
    """
    releases = list_releases(token, full_name)
    for release in releases:
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            if package_identifier in name:
                return {
                    "tag": release.get("tag_name"),
                    "release_id": release.get("id"),
                    "asset_name": name,
                    "download_url": asset.get("browser_download_url", ""),
                    "size": asset.get("size", 0),
                }
    return None


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _get_release_by_tag(token: str, full_name: str, tag_name: str) -> dict | None:
    """GET /repos/{o}/{r}/releases/tags/{tag} → release dict hoặc None."""
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/releases/tags/{tag_name}"
    try:
        resp = requests.get(
            url,
            headers={**_gh_headers(token, json_body=False), "Content-Type": ""},
            timeout=10,
        )
    except requests.RequestException:
        return None
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()


def _get_release_by_id(token: str, full_name: str, release_id: int) -> dict | None:
    """GET /repos/{o}/{r}/releases/{id} → release dict hoặc None."""
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/releases/{release_id}"
    try:
        resp = requests.get(
            url,
            headers={**_gh_headers(token, json_body=False), "Content-Type": ""},
            timeout=10,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()
