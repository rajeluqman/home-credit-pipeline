"""Publish this repo's real docs/ set to Confluence as living documentation.

Ported from creative_intelligence_lab's scripts/sync_docs_to_confluence.py (pipeline-retrofit
effort). CIL's version published a curated `confluence/` hub-page set; this repo has no such
hub set yet, so PUBLISH_SET below publishes the real `docs/*.md` + `docs/ADR/*.md` files
directly, in reading order. Confluence Cloud REST API only (Basic Auth: email + API token).
An existing page is found by title and updated (version-incremented), never duplicated.

Manual run only — not wired into CI or the Airflow DAGs.

Usage:
    python scripts/sync_docs_to_confluence.py             # real run, needs the 5 env vars
    python scripts/sync_docs_to_confluence.py --dry-run    # render + list, no API calls, no creds
    python scripts/sync_docs_to_confluence.py --prune       # also DELETE live pages no longer in
                                                            # the curated set
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import markdown
import requests

REPO_DIR = Path(__file__).resolve().parent.parent
PROJECT_PREFIX = "Home Credit Risk Pipeline"

REQUIRED_ENV = [
    "CONFLUENCE_BASE_URL",  # e.g. https://yourcompany.atlassian.net/wiki
    "CONFLUENCE_EMAIL",
    "CONFLUENCE_API_TOKEN",
    "CONFLUENCE_SPACE_KEY",
    "CONFLUENCE_PARENT_PAGE_ID",
]

# Reading order, (repo-relative path, explicit page-name or None).
# None -> page name is the file stem (keeps idempotency with already-created pages).
PUBLISH_SET: list[tuple[str, str | None]] = [
    ("docs/BRD.md", None),
    ("docs/DRD.md", None),
    ("docs/DATA_DICTIONARY.md", None),
    ("docs/DATA_MODEL.md", None),
    ("docs/ARCHITECTURE.md", None),
    ("docs/PIPELINE_SPEC.md", None),
    ("docs/ADR/ADR-001-kimball-star-schema.md", "ADR-001 Kimball Star Schema"),
    ("docs/ADR/ADR-002-pii-mask-order.md", "ADR-002 PII Mask Order"),
    ("docs/ADR/ADR-003-kimball-over-obt-sizing.md", "ADR-003 Kimball-over-OBT Sizing"),
    ("docs/DQD.md", None),
    ("docs/OPS_RUNBOOK.md", None),
    ("INTERVIEW_GUIDE.md", None),
    ("PROJECT_STATUS.md", None),
]


def _page_title(rel_path: str, name: str | None) -> str:
    stem = name if name is not None else Path(rel_path).stem
    return f"{PROJECT_PREFIX} — {stem}"


def _published() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for rel, name in PUBLISH_SET:
        p = REPO_DIR / rel
        if not p.exists():
            sys.exit(f"sync_docs_to_confluence: curated doc missing on disk: {rel}")
        out.append((p, _page_title(rel, name)))
    return out


def _to_confluence_storage_html(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=["tables", "fenced_code"])


def _assert_env(env: dict[str, str]) -> None:
    missing = [k for k in REQUIRED_ENV if not env.get(k)]
    if missing:
        sys.exit(
            f"sync_docs_to_confluence: missing required env var(s): {', '.join(missing)} — "
            "refusing to run. Use --dry-run to preview without credentials."
        )


def _find_existing_page(base_url: str, auth, space_key: str, title: str) -> dict | None:
    resp = requests.get(
        f"{base_url}/rest/api/content",
        params={"title": title, "spaceKey": space_key, "expand": "version"},
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0] if results else None


TITLE_PREFIX = f"{PROJECT_PREFIX} — "


def _list_project_pages(base_url: str, auth, space_key: str) -> list[dict]:
    pages: list[dict] = []
    start = 0
    while True:
        resp = requests.get(
            f"{base_url}/rest/api/content",
            params={"spaceKey": space_key, "type": "page", "limit": 100, "start": start},
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        pages += [p for p in results if p.get("title", "").startswith(TITLE_PREFIX)]
        if len(results) < 100:
            return pages
        start += 100


def _create_page(base_url: str, auth, space_key: str, parent_id: str, title: str, html: str) -> str:
    resp = requests.post(
        f"{base_url}/rest/api/content",
        auth=auth,
        json={
            "type": "page",
            "title": title,
            "space": {"key": space_key},
            "ancestors": [{"id": parent_id}],
            "body": {"storage": {"value": html, "representation": "storage"}},
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def _update_page(base_url: str, auth, page_id: str, next_version: int, title: str, html: str) -> None:
    resp = requests.put(
        f"{base_url}/rest/api/content/{page_id}",
        auth=auth,
        json={
            "type": "page",
            "title": title,
            "version": {"number": next_version},
            "body": {"storage": {"value": html, "representation": "storage"}},
        },
        timeout=30,
    )
    resp.raise_for_status()


def _delete_page(base_url: str, auth, page_id: str) -> None:
    resp = requests.delete(f"{base_url}/rest/api/content/{page_id}", auth=auth, timeout=30)
    resp.raise_for_status()


def sync(env: dict[str, str], dry_run: bool, prune: bool) -> None:
    docs = _published()
    keep_titles = {title for _, title in docs}

    if dry_run:
        print(f"[dry-run] would publish {len(docs)} curated doc(s) — no API calls made:")
        for path, title in docs:
            html = _to_confluence_storage_html(path.read_text())
            print(f"  + {title}  ({len(html)} chars, from {path.relative_to(REPO_DIR)})")
        return

    _assert_env(env)
    base_url = env["CONFLUENCE_BASE_URL"].rstrip("/")
    auth = (env["CONFLUENCE_EMAIL"], env["CONFLUENCE_API_TOKEN"])
    space_key = env["CONFLUENCE_SPACE_KEY"]
    parent_id = env["CONFLUENCE_PARENT_PAGE_ID"]

    for path, title in docs:
        html = _to_confluence_storage_html(path.read_text())
        existing = _find_existing_page(base_url, auth, space_key, title)
        if existing:
            next_version = existing["version"]["number"] + 1
            _update_page(base_url, auth, existing["id"], next_version, title, html)
            print(f"updated: {title} (v{next_version})")
        else:
            page_id = _create_page(base_url, auth, space_key, parent_id, title, html)
            print(f"created: {title} (id={page_id})")

    if prune:
        live = _list_project_pages(base_url, auth, space_key)
        orphans = [p for p in live if p["title"] not in keep_titles and p["id"] != parent_id]
        print(f"\n--prune: {len(orphans)} live page(s) not in the curated set — deleting:")
        for p in orphans:
            _delete_page(base_url, auth, p["id"])
            print(f"  deleted: {p['title']} (id={p['id']})")


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="render + list pages, no API calls, no credentials required"
    )
    parser.add_argument(
        "--prune", action="store_true", help="DELETE live pages (PROJECT_PREFIX) no longer in the curated set"
    )
    args = parser.parse_args()
    sync(dict(os.environ), args.dry_run, args.prune)
