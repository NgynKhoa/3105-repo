"""
github_write.py — Ghi data vào GitHub repo qua Contents API.

Hai mode:
  1. PR mode (mặc định, an toàn):
     - Tạo branch mới từ default_branch
     - Commit thay đổi trên branch đó
     - Tạo Pull Request về default_branch
     - Trả URL của PR

  2. Direct push (chỉ khi user chọn, cần scope repo):
     - Commit thẳng lên default_branch
     - Trả URL của commit

Cả 2 mode dùng PUT /repos/{owner}/{repo}/contents/{path}:
  - Nếu file đã tồn tại → cần `sha` của file cũ (GitHub yêu cầu để chống ghi đè).
  - Nếu file mới → không cần sha.
  - Body JSON: {message, content (base64), sha?, branch?}

Đối với `repo.json` (file identifier), admin thường không sửa → có thể coi là
read-only sau khi tạo. Sửa đổi chủ yếu là `repo.yml` + assets.

Bảo mật:
  - Token lấy từ session (HttpOnly), KHÔNG nhận từ client.
  - Verify ownership trước khi ghi (qua owner_required decorator ở route layer).
  - Validate input: slug không chứa `..`, path không có leading `/`,
    commit message không quá dài.
"""
from __future__ import annotations

import base64
import re
import secrets
import urllib.parse
from typing import Any

import requests
from flask import current_app, jsonify, request

from .config import Config


# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------

_SLUG_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}$")
_PATH_RE = re.compile(r"^(?!\.)(?!/)(?!.*\.\.)[a-zA-Z0-9._/-]{1,200}$")
_BRANCH_RE = re.compile(r"^(?!-)(?!.*\.\.)[a-zA-Z0-9._/-]{1,100}$")


def _validate_inputs(slug: str, path: str, content: str, commit_message: str) -> str | None:
    """Trả về None nếu OK, error message nếu invalid."""
    if not _SLUG_RE.match(slug):
        return f"slug không hợp lệ: {slug!r}"
    if not _PATH_RE.match(path):
        return f"path không hợp lệ: {path!r}"
    if len(content) > 5_000_000:  # 5MB
        return "content quá lớn (>5MB)"
    if len(commit_message) > 200:
        return "commit_message quá dài (>200 chars)"
    if not commit_message.strip():
        return "commit_message không được rỗng"
    return None


def _gh_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "3105-repo-builder/1.0",
    }


def _get_repo_metadata(token: str, full_name: str) -> dict:
    """GET /repos/{owner}/{repo} → metadata (default_branch, etc.)."""
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}"
    resp = requests.get(url, headers=_gh_headers(token), timeout=10)
    if resp.status_code == 404:
        raise FileNotFoundError(f"Repo {full_name} không tồn tại hoặc bạn không có quyền truy cập")
    resp.raise_for_status()
    return resp.json()


def _get_file_sha(token: str, full_name: str, path: str, branch: str) -> str | None:
    """GET contents/{path}?ref={branch} → sha (cần thiết khi update file).
    Trả None nếu file chưa tồn tại.
    """
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/contents/{path}"
    resp = requests.get(
        url, headers=_gh_headers(token), params={"ref": branch}, timeout=10,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json().get("sha")


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def write_file(
    token: str,
    full_name: str,
    path: str,
    content: str,
    commit_message: str,
    *,
    mode: str = "pr",  # "pr" hoặc "direct"
) -> dict[str, Any]:
    """Ghi file vào GitHub repo.

    Args:
      token: GitHub access token (từ session).
      full_name: "owner/repo".
      path: file path trong repo (vd "repo.yml", "assets/icon/x.png").
      content: file content (UTF-8 text).
      commit_message: commit message.
      mode: "pr" → tạo branch + PR, "direct" → push lên default branch.

    Returns: {
      "ok": True,
      "mode": "pr" | "direct",
      "branch": str,
      "commit_sha": str,
      "commit_url": str,
      "pr_url": str | None,  # chỉ có ở mode "pr"
      "pr_number": int | None,
    }
    """
    if mode not in ("pr", "direct"):
        raise ValueError(f"mode phải là 'pr' hoặc 'direct', nhận được {mode!r}")

    # 1. Lấy metadata repo
    meta = _get_repo_metadata(token, full_name)
    default_branch = meta.get("default_branch", "main")
    owner = meta.get("owner", {}).get("login", "")

    # 2. Xác định target branch
    if mode == "direct":
        target_branch = default_branch
        pr_url, pr_number = None, None
    else:
        # Tạo branch mới từ default_branch
        target_branch = _create_branch(token, full_name, default_branch)
        pr_url, pr_number = None, None

    # 3. Lấy SHA file cũ (nếu có)
    existing_sha = _get_file_sha(token, full_name, path, target_branch)

    # 4. Commit file mới
    encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
    put_url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/contents/{path}"
    put_body = {
        "message": commit_message,
        "content": encoded,
        "branch": target_branch,
    }
    if existing_sha:
        put_body["sha"] = existing_sha

    put_resp = requests.put(
        put_url, headers=_gh_headers(token), json=put_body, timeout=30,
    )
    if put_resp.status_code not in (200, 201):
        raise RuntimeError(
            f"PUT contents failed: {put_resp.status_code} {put_resp.text[:300]}"
        )
    put_data = put_resp.json()
    commit_sha = put_data.get("commit", {}).get("sha", "")
    commit_url = put_data.get("commit", {}).get("html_url", "")

    # 5. Nếu PR mode → tạo PR
    if mode == "pr":
        pr_url, pr_number = _create_pr(
            token, full_name, target_branch, default_branch,
            title=commit_message,
            body=(
                "🤖 Được tạo tự động qua 3105-repo Builder.\n\n"
                f"- Branch: `{target_branch}`\n"
                f"- File: `{path}`\n"
                f"- Author: 3105-repo Builder\n"
            ),
        )

    return {
        "ok": True,
        "mode": mode,
        "branch": target_branch,
        "commit_sha": commit_sha,
        "commit_url": commit_url,
        "pr_url": pr_url,
        "pr_number": pr_number,
        "owner": owner,
        "repo": full_name.split("/", 1)[-1] if "/" in full_name else full_name,
    }


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _create_branch(token: str, full_name: str, from_branch: str) -> str:
    """Tạo branch mới từ default_branch. Tên branch: 3105-edit-<random>."""
    # Lấy SHA của commit HEAD trên from_branch
    ref_url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/git/refs/heads/{from_branch}"
    ref_resp = requests.get(ref_url, headers=_gh_headers(token), timeout=10)
    ref_resp.raise_for_status()
    head_sha = ref_resp.json()["object"]["sha"]

    # Tên branch unique
    new_branch = f"3105-edit-{secrets.token_hex(6)}"
    # Đảm bảo tên hợp lệ (theo Git naming)
    while not _BRANCH_RE.match(new_branch):
        new_branch = f"3105-edit-{secrets.token_hex(6)}"

    # Tạo ref
    create_url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/git/refs"
    create_resp = requests.post(
        create_url,
        headers=_gh_headers(token),
        json={"ref": f"refs/heads/{new_branch}", "sha": head_sha},
        timeout=10,
    )
    if create_resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Tạo branch thất bại: {create_resp.status_code} {create_resp.text[:300]}"
        )
    return new_branch


def _create_pr(
    token: str, full_name: str, head: str, base: str, *, title: str, body: str,
) -> tuple[str, int]:
    """POST /repos/{o}/{r}/pulls → (html_url, number)."""
    url = f"{Config.GITHUB_API_BASE}/repos/{full_name}/pulls"
    resp = requests.post(
        url, headers=_gh_headers(token),
        json={"title": title, "head": head, "base": base, "body": body},
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Tạo PR thất bại: {resp.status_code} {resp.text[:300]}"
        )
    data = resp.json()
    return data.get("html_url", ""), data.get("number", 0)
