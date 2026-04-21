#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

NOTEBOOKLM_SUPPORTED_LOCAL_EXTENSIONS = {
    "3g2",
    "3gp",
    "aac",
    "aif",
    "aifc",
    "aiff",
    "amr",
    "au",
    "avi",
    "avif",
    "bmp",
    "cda",
    "csv",
    "docx",
    "epub",
    "gif",
    "heic",
    "heif",
    "ico",
    "jp2",
    "jpe",
    "jpeg",
    "jpg",
    "m4a",
    "md",
    "mid",
    "mp3",
    "mp4",
    "mpeg",
    "ogg",
    "opus",
    "pdf",
    "png",
    "pptx",
    "ra",
    "ram",
    "snd",
    "tif",
    "tiff",
    "txt",
    "wav",
    "webp",
    "wma",
}


@dataclass(frozen=True)
class AttachmentCandidate:
    title: str
    attachment_key: str
    relative_path: str
    file_path: Path

    @property
    def filename(self) -> str:
        return self.file_path.name

    @property
    def extension(self) -> str:
        return self.file_path.suffix.lower().lstrip(".")


class ImportError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import Zotero attachments into NotebookLM via nlm.",
    )
    parser.add_argument("--collection", required=True, help="Exact Zotero collection name")
    parser.add_argument("--notebook-base", required=True, help="NotebookLM base notebook name")
    parser.add_argument("--profile", default=None, help="NotebookLM profile for nlm")
    parser.add_argument(
        "--title-match",
        action="append",
        default=[],
        help="Match Zotero item titles by case-insensitive normalized substring; repeatable",
    )
    parser.add_argument(
        "--extension",
        action="append",
        default=[],
        help="Attachment extension to upload; repeatable and comma-separated. Default: pdf",
    )
    parser.add_argument(
        "--max-per-notebook",
        type=int,
        default=50,
        help="Maximum attachments per notebook shard",
    )
    parser.add_argument(
        "--zotero-db",
        default="~/Zotero/zotero.sqlite",
        help="Path to Zotero SQLite database",
    )
    parser.add_argument(
        "--zotero-storage",
        default="~/Zotero/storage",
        help="Path to Zotero storage directory",
    )
    parser.add_argument(
        "--wait-timeout",
        type=float,
        default=600.0,
        help="Timeout passed to nlm source add --wait-timeout",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    zotero_db = Path(args.zotero_db).expanduser().resolve()
    zotero_storage = Path(args.zotero_storage).expanduser().resolve()
    extensions = parse_extensions(args.extension)
    title_filters = [value for value in args.title_match if value.strip()]

    try:
        if args.max_per_notebook <= 0:
            raise ImportError("--max-per-notebook must be positive")

        ensure_nlm_available()
        ensure_authenticated(args.profile)
        attachments = load_collection_attachments(
            args.collection,
            zotero_db,
            zotero_storage,
            extensions=extensions,
            title_filters=title_filters,
        )
        if not attachments:
            title_suffix = ""
            if title_filters:
                title_suffix = f" matching title filters {title_filters}"
            raise ImportError(
                f"Collection '{args.collection}' contains no attachments with extensions "
                f"{sorted(extensions)}{title_suffix}"
            )

        notebook_titles = shard_titles(args.notebook_base, len(attachments), args.max_per_notebook)
        shards = chunked(attachments, args.max_per_notebook)

        uploaded = 0
        skipped = 0
        failures: list[str] = []
        touched_notebooks: list[str] = []

        for title, shard in zip(notebook_titles, shards, strict=True):
            notebook = get_or_create_notebook(title, args.profile)
            touched_notebooks.append(f"{title} ({notebook['id']})")

            existing_sources = list_sources(notebook["id"], args.profile)
            existing_keys = build_existing_source_keys(existing_sources)
            pending = [item for item in shard if not is_duplicate(item, existing_keys)]
            skipped += len(shard) - len(pending)

            if len(existing_sources) + len(pending) > args.max_per_notebook:
                raise ImportError(
                    f"Notebook '{title}' would exceed {args.max_per_notebook} sources "
                    f"({len(existing_sources)} existing + {len(pending)} new)"
                )

            for item in pending:
                try:
                    add_file_source(
                        notebook["id"],
                        item.file_path,
                        args.profile,
                        args.wait_timeout,
                    )
                    existing_keys.update(candidate_keys(item))
                    uploaded += 1
                except ImportError as exc:
                    failures.append(f"{item.file_path}: {exc}")

        print_summary(
            collection=args.collection,
            notebook_base=args.notebook_base,
            total=len(attachments),
            extensions=sorted(extensions),
            title_filters=title_filters,
            touched_notebooks=touched_notebooks,
            uploaded=uploaded,
            skipped=skipped,
            failures=failures,
        )
        return 0 if not failures else 1
    except ImportError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def ensure_nlm_available() -> None:
    if shutil.which("nlm") is None:
        raise ImportError(
            "nlm is not installed or not on PATH. Install it with: uv tool install notebooklm-mcp-cli"
        )


def ensure_authenticated(profile: str | None) -> None:
    args = ["login", "--check"]
    if profile:
        args.extend(["--profile", profile])
    check = run_nlm(args, allow_failure=True)
    if check.returncode == 0:
        return

    login_args = ["login"]
    if profile:
        login_args.extend(["--profile", profile])
    print("NotebookLM authentication is missing or expired. Launching 'nlm login'...")
    login = run_nlm(login_args, interactive=True, allow_failure=True)
    if login.returncode != 0:
        raise ImportError("Interactive 'nlm login' failed")

    check = run_nlm(args, allow_failure=True)
    if check.returncode != 0:
        message = check.stderr.strip() or check.stdout.strip() or "authentication check failed"
        raise ImportError(f"Authentication still invalid after login: {message}")


def connect_sqlite(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise ImportError(f"Zotero database not found: {db_path}")
    uri = f"file:{db_path}?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def load_collection_attachments(
    collection_name: str,
    zotero_db: Path,
    zotero_storage: Path,
    *,
    extensions: set[str],
    title_filters: list[str],
) -> list[AttachmentCandidate]:
    if not zotero_storage.exists():
        raise ImportError(f"Zotero storage directory not found: {zotero_storage}")

    with connect_sqlite(zotero_db) as conn:
        exact_matches = conn.execute(
            """
            SELECT collectionID, collectionName
            FROM collections
            WHERE collectionName = ?
            ORDER BY collectionID
            """,
            (collection_name,),
        ).fetchall()

        if not exact_matches:
            similar = conn.execute(
                """
                SELECT collectionName
                FROM collections
                WHERE lower(collectionName) LIKE lower(?)
                ORDER BY collectionName
                LIMIT 10
                """,
                (f"%{collection_name}%",),
            ).fetchall()
            hint = ""
            if similar:
                hint = " Similar collections: " + ", ".join(row["collectionName"] for row in similar)
            raise ImportError(f"Collection '{collection_name}' not found.{hint}")

        if len(exact_matches) > 1:
            raise ImportError(
                f"Collection name '{collection_name}' is ambiguous; found {len(exact_matches)} exact matches"
            )

        collection_id = exact_matches[0]["collectionID"]
        rows = conn.execute(
            """
            WITH RECURSIVE coll AS (
              SELECT collectionID
              FROM collections
              WHERE collectionID = ?
              UNION ALL
              SELECT c.collectionID
              FROM collections c
              JOIN coll p ON c.parentCollectionID = p.collectionID
            ),
            parent_items AS (
              SELECT DISTINCT ci.itemID
              FROM collectionItems ci
              JOIN coll ON coll.collectionID = ci.collectionID
            ),
            titles AS (
              SELECT p.itemID,
                     MAX(CASE WHEN f.fieldName = 'title' THEN v.value END) AS title
              FROM parent_items p
              LEFT JOIN itemData d ON d.itemID = p.itemID
              LEFT JOIN fieldsCombined f ON f.fieldID = d.fieldID
              LEFT JOIN itemDataValues v ON v.valueID = d.valueID
              GROUP BY p.itemID
            )
            SELECT COALESCE(t.title, '') AS title,
                   attach.key AS attachment_key,
                   ia.path AS attachment_path,
                   ia.contentType AS content_type
            FROM parent_items p
            JOIN itemAttachments ia
              ON ia.parentItemID = p.itemID
            JOIN items attach ON attach.itemID = ia.itemID
            LEFT JOIN titles t ON t.itemID = p.itemID
            ORDER BY lower(COALESCE(t.title, '')), attach.key
            """,
            (collection_id,),
        ).fetchall()

    attachments: list[AttachmentCandidate] = []
    for row in rows:
        title = row["title"].strip()
        stored_path = row["attachment_path"] or ""
        stored_extension = extension_from_stored_path(stored_path)
        if stored_extension not in extensions:
            continue
        effective_title = title or Path(stored_path.split("storage:", 1)[-1]).stem
        if title_filters and not matches_title_filters(effective_title, title_filters):
            continue
        file_path = resolve_attachment_path(
            attachment_key=row["attachment_key"],
            stored_path=stored_path,
            zotero_storage=zotero_storage,
        )
        candidate = AttachmentCandidate(
            title=effective_title or file_path.stem,
            attachment_key=row["attachment_key"],
            relative_path=stored_path,
            file_path=file_path,
        )
        attachments.append(candidate)

    return attachments


def parse_extensions(values: list[str]) -> set[str]:
    if not values:
        return {"pdf"}
    extensions: set[str] = set()
    for value in values:
        for part in value.split(","):
            cleaned = part.strip().lower().lstrip(".")
            if cleaned:
                extensions.add(cleaned)
    if not extensions:
        raise ImportError("At least one non-empty extension is required")
    unsupported = sorted(extensions - NOTEBOOKLM_SUPPORTED_LOCAL_EXTENSIONS)
    if unsupported:
        supported = ", ".join(sorted(NOTEBOOKLM_SUPPORTED_LOCAL_EXTENSIONS))
        raise ImportError(
            "NotebookLM does not officially support these local upload extensions: "
            f"{', '.join(unsupported)}. Supported extensions: {supported}"
        )
    return extensions


def matches_title_filters(title: str, filters: list[str]) -> bool:
    normalized_title = normalize_text(title)
    return any(normalize_text(pattern) in normalized_title for pattern in filters)


def extension_from_stored_path(stored_path: str) -> str:
    if not stored_path:
        return ""
    if stored_path.startswith("storage:"):
        stored_path = stored_path.split("storage:", 1)[1]
    return Path(stored_path).suffix.lower().lstrip(".")


def resolve_attachment_path(
    attachment_key: str,
    stored_path: str,
    zotero_storage: Path,
) -> Path:
    if not stored_path:
        raise ImportError(f"Attachment {attachment_key} has an empty path")

    if stored_path.startswith("storage:"):
        relative_name = stored_path.split("storage:", 1)[1]
        resolved = zotero_storage / attachment_key / relative_name
    else:
        resolved = Path(stored_path).expanduser()
        if not resolved.is_absolute():
            resolved = zotero_storage / attachment_key / resolved

    resolved = resolved.resolve()
    if not resolved.exists():
        raise ImportError(f"Attachment file not found: {resolved}")
    return resolved


def shard_titles(base: str, total: int, max_per_notebook: int) -> list[str]:
    shard_count = (total + max_per_notebook - 1) // max_per_notebook
    if shard_count == 1:
        return [base]
    return [f"{base}_{index:02d}" for index in range(1, shard_count + 1)]


def chunked(items: list[AttachmentCandidate], size: int) -> list[list[AttachmentCandidate]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def list_notebooks(profile: str | None) -> list[dict]:
    stdout = run_nlm(["notebook", "list", "--json"], profile=profile, json_output=True)
    if not isinstance(stdout, list):
        raise ImportError("Unexpected output from 'nlm notebook list --json'")
    return stdout


def get_or_create_notebook(title: str, profile: str | None) -> dict[str, str]:
    matches = [notebook for notebook in list_notebooks(profile) if notebook.get("title") == title]
    if len(matches) > 1:
        raise ImportError(f"Multiple notebooks already use the title '{title}'")
    if len(matches) == 1:
        return {"id": matches[0]["id"], "title": title}

    stdout = run_nlm(["notebook", "create", title], profile=profile)
    match = re.search(r"^\s*ID:\s*([0-9a-f-]+)\s*$", stdout, re.MULTILINE)
    if not match:
        raise ImportError(f"Could not parse notebook ID from create output for '{title}'")
    return {"id": match.group(1), "title": title}


def list_sources(notebook_id: str, profile: str | None) -> list[dict]:
    stdout = run_nlm(
        ["source", "list", notebook_id, "--json"],
        profile=profile,
        json_output=True,
    )
    if not isinstance(stdout, list):
        raise ImportError(f"Unexpected output from 'nlm source list {notebook_id} --json'")
    return stdout


def add_file_source(
    notebook_id: str,
    file_path: Path,
    profile: str | None,
    wait_timeout: float,
) -> None:
    run_nlm(
        [
            "source",
            "add",
            notebook_id,
            "--file",
            str(file_path),
            "--wait",
            "--wait-timeout",
            str(wait_timeout),
        ],
        profile=profile,
    )


def build_existing_source_keys(sources: list[dict]) -> set[str]:
    keys: set[str] = set()
    for source in sources:
        title = str(source.get("title", "")).strip()
        keys.update(source_title_keys(title))
    return keys


def is_duplicate(item: AttachmentCandidate, existing_keys: set[str]) -> bool:
    return not candidate_keys(item).isdisjoint(existing_keys)


def candidate_keys(item: AttachmentCandidate) -> set[str]:
    keys = set()
    keys.update(source_title_keys(item.file_path.name))
    keys.update(source_title_keys(item.file_path.stem))
    keys.update(source_title_keys(item.title))
    return {key for key in keys if key}


def source_title_keys(text: str) -> set[str]:
    raw = normalize_text(text)
    stem = normalize_text(Path(text).stem)
    return {key for key in {raw, stem} if key}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    normalized = re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def run_nlm(
    args: list[str],
    *,
    profile: str | None = None,
    json_output: bool = False,
    interactive: bool = False,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str] | str | list | dict:
    command = ["nlm", *args]
    if profile:
        command.extend(["--profile", profile])

    if interactive:
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode != 0 and not allow_failure:
            raise ImportError(f"{' '.join(command)} failed with exit code {completed.returncode}")
        return completed

    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if allow_failure:
        return completed

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "nlm command failed"
        raise ImportError(f"{' '.join(command)}: {message}")

    stdout = completed.stdout.strip()
    if json_output:
        try:
            return json.loads(stdout or "null")
        except json.JSONDecodeError as exc:
            raise ImportError(f"Failed to parse JSON from {' '.join(command)}") from exc
    return stdout


def print_summary(
    *,
    collection: str,
    notebook_base: str,
    total: int,
    extensions: list[str],
    title_filters: list[str],
    touched_notebooks: list[str],
    uploaded: int,
    skipped: int,
    failures: list[str],
) -> None:
    print(f"Collection: {collection}")
    print(f"Notebook base: {notebook_base}")
    print(f"Extensions: {', '.join(extensions)}")
    print(f"Title filters: {title_filters if title_filters else '[all items]'}")
    print(f"Attachments discovered: {total}")
    print("Notebooks:")
    for notebook in touched_notebooks:
        print(f"  - {notebook}")
    print(f"Uploaded: {uploaded}")
    print(f"Skipped existing: {skipped}")
    print(f"Failures: {len(failures)}")
    for failure in failures:
        print(f"  - {failure}")


if __name__ == "__main__":
    raise SystemExit(main())
