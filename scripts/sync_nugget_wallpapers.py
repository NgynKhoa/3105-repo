#!/usr/bin/env python3
"""Sync Nugget-Wallpapers packages into the main 3105 repository."""

from __future__ import annotations

import json
import pathlib
import urllib.parse
import urllib.request


UPSTREAM_API = "https://api.github.com/repos/SerStars/Nugget-Wallpapers/commits/main"
UPSTREAM_RAW_PREFIX = (
    "https://raw.githubusercontent.com/SerStars/Nugget-Wallpapers/"
)
CATALOGS = ("apple", "custom")
OUTPUT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "repositories"
    / "demo"
    / "repo.json"
)
SUPPORTED_OS = [
    {"minimum": "17.0", "maximum": "18.7.1"},
    {"minimum": "26.0", "maximum": "26.6.1"},
    {
        "minimum": "27.0",
        "maximum": "27.0",
        "builds": ["24A5355q", "24A5370h", "24A5380h", "24A5390f"],
    },
]


def supported_os(summary: str | None) -> list[dict[str, object]]:
    normalized = (summary or "").casefold()
    if "ios 26.3.1" in normalized:
        return [
            {"minimum": "26.3.1", "maximum": "26.6.1"},
            SUPPORTED_OS[2],
        ]
    if "ios 26" in normalized:
        return SUPPORTED_OS[1:]
    if "ios 18" in normalized:
        return [
            {"minimum": "18.0", "maximum": "18.7.1"},
            *SUPPORTED_OS[1:],
        ]
    return SUPPORTED_OS


def request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": "3105-repo-sync"})


def load_revision() -> str:
    with urllib.request.urlopen(request(UPSTREAM_API), timeout=60) as response:
        document = json.load(response)
    revision = document.get("sha") if isinstance(document, dict) else None
    if (
        not isinstance(revision, str)
        or len(revision) != 40
        or any(character not in "0123456789abcdefABCDEF" for character in revision)
    ):
        raise RuntimeError("invalid upstream revision")
    return revision.lower()


def load_catalog(
    category: str,
    *,
    upstream_root: str,
) -> list[dict[str, object]]:
    url = urllib.parse.urljoin(upstream_root, f"wallpapers-{category}.json")
    with urllib.request.urlopen(request(url), timeout=60) as response:
        if urllib.parse.urlparse(response.geturl()).scheme != "https":
            raise RuntimeError(f"insecure catalog redirect: {response.geturl()}")
        documents = json.load(response)
    if not isinstance(documents, list):
        raise RuntimeError(f"invalid {category} catalog")
    return documents


def resolved_url(raw_url: object, *, catalog_url: str) -> str:
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise RuntimeError("missing upstream URL")
    url = urllib.parse.urljoin(catalog_url, raw_url.strip())
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError(f"insecure upstream URL: {url}")
    encoded_path = urllib.parse.quote(
        urllib.parse.unquote(parsed.path),
        safe="/",
    )
    return urllib.parse.urlunparse(parsed._replace(path=encoded_path))


def normalized_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def single_line_text(value: object) -> str | None:
    value = normalized_text(value)
    return " ".join(value.split()) if value is not None else None


def package_metadata(
    category: str,
    document: dict[str, object],
    *,
    upstream_root: str,
) -> dict[str, object]:
    source_id = document.get("id")
    name = single_line_text(document.get("name"))
    if not isinstance(source_id, int) or source_id < 0 or name is None:
        raise RuntimeError(f"invalid {category} wallpaper entry")

    catalog_url = urllib.parse.urljoin(
        upstream_root, f"wallpapers-{category}.json"
    )
    download_url = resolved_url(document.get("url"), catalog_url=catalog_url)
    preview_url = resolved_url(document.get("preview"), catalog_url=catalog_url)
    if pathlib.PurePosixPath(urllib.parse.urlparse(download_url).path).suffix.lower() != ".tendies":
        raise RuntimeError(f"unsupported package type: {download_url}")

    upstream_summary = single_line_text(document.get("description"))
    summary = upstream_summary or "Wallpaper .tendies từ Nugget-Wallpapers."
    author = single_line_text(document.get("authors")) or "Nugget-Wallpapers"
    category_name = "Apple" if category == "apple" else "Custom"

    return {
        "identifier": f"nugget-{category}-{source_id}",
        "kind": "wallpaper",
        "name": name,
        "author": author,
        "version": "1.0.0",
        "summary": summary,
        "description": (
            f"{summary}\n\nNguồn: SerStars/Nugget-Wallpapers (GPL-3.0)."
        ),
        "category": "Wallpaper",
        "tags": ["Wallpaper", category_name],
        "icon": preview_url,
        "screenshots": [preview_url],
        "download": download_url,
        "supportedOS": supported_os(upstream_summary),
        "featured": False,
        "isPrivate": False,
    }


def main() -> None:
    revision = load_revision()
    upstream_root = f"{UPSTREAM_RAW_PREFIX}{revision}/"
    packages: list[dict[str, object]] = []
    skipped: list[str] = []
    for category in CATALOGS:
        catalog_url = urllib.parse.urljoin(
            upstream_root, f"wallpapers-{category}.json"
        )
        for document in load_catalog(category, upstream_root=upstream_root):
            if not isinstance(document, dict):
                raise RuntimeError(f"invalid {category} wallpaper entry")
            download_url = resolved_url(document.get("url"), catalog_url=catalog_url)
            if not download_url.startswith(upstream_root):
                skipped.append(normalized_text(document.get("name")) or download_url)
                continue
            packages.append(
                package_metadata(
                    category,
                    document,
                    upstream_root=upstream_root,
                )
            )
    with OUTPUT.open(encoding="utf-8") as repository_file:
        repository = json.load(repository_file)
    existing_packages = repository.get("packages")
    if (
        repository.get("schemaVersion") != 1
        or repository.get("identifier") != "com.yangjiii.3105"
        or not isinstance(existing_packages, list)
    ):
        raise RuntimeError("invalid main 3105 repository")
    patch_packages = [
        package
        for package in existing_packages
        if isinstance(package, dict) and package.get("kind", "patch") != "wallpaper"
    ]
    repository["packages"] = [*patch_packages, *packages]
    OUTPUT.write_text(
        json.dumps(repository, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Pinned Nugget-Wallpapers revision {revision}")
    print(
        f"Wrote {len(patch_packages)} patches + {len(packages)} wallpapers "
        f"to {OUTPUT}"
    )
    if skipped:
        print("Skipped non-commit-pinned packages: " + ", ".join(skipped))


if __name__ == "__main__":
    main()
