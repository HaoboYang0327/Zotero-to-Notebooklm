---
name: notebooklm-zotero-import
description: "Import local Zotero attachments into NotebookLM notebooks through notebooklm-mcp-cli (`nlm`). Use when Codex needs to find specific Zotero items by title, upload their local files to NotebookLM, default to PDF-only imports, include additional NotebookLM-supported formats when requested, auto-login to `nlm` if needed, shard notebooks at 50 files each, or avoid duplicate uploads on reruns."
---

# NotebookLM Zotero Import

Import a Zotero collection's local attachments into NotebookLM with deterministic naming, rerun-safe behavior, and default PDF filtering.

Use the bundled script instead of reimplementing the workflow in-line.

## Prerequisites

Verify these before running the import:
- `nlm` is installed and on `PATH`
- Zotero data exists locally, usually at `~/Zotero/zotero.sqlite` and `~/Zotero/storage`

Do not manually pre-check auth in normal use. The script always runs `nlm login --check` first and launches `nlm login` automatically when the session is missing or expired.

## Workflow

1. Run the importer with `uv run`.

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --notebook-base "LOB_TTT"
```

2. Let the script do the full workflow:
- check `nlm` login state and run `nlm login` when required
- open Zotero SQLite in read-only immutable mode
- resolve the collection by exact name
- walk descendant collections
- optionally narrow Zotero items by normalized title substring with `--title-match`
- resolve each attachment to a real file under Zotero storage
- keep only requested NotebookLM-supported local upload extensions; default `pdf`
- split uploads into notebook shards of at most 50 files
- reuse an existing same-name notebook when it is unique
- skip files already present in the target notebook based on normalized titles and filenames
- upload missing files through `nlm source add --file ... --wait`

The script fails fast on extensions that are not in NotebookLM's official local-upload list. As of April 21, 2026, that list includes:
- documents: `pdf`, `docx`, `txt`, `md`, `csv`, `pptx`, `epub`
- images: `avif`, `bmp`, `gif`, `heic`, `heif`, `ico`, `jp2`, `jpe`, `jpeg`, `jpg`, `png`, `tif`, `tiff`, `webp`
- audio and media: `3g2`, `3gp`, `aac`, `aif`, `aifc`, `aiff`, `amr`, `au`, `avi`, `cda`, `m4a`, `mid`, `mp3`, `mp4`, `mpeg`, `ogg`, `opus`, `ra`, `ram`, `snd`, `wav`, `wma`

Extensions outside that set, such as `mlx`, are rejected locally before upload.

3. Read the final summary for:
- notebooks touched
- files uploaded
- files skipped as already present
- failures, if any

## Naming Rules

- Use the base name unchanged when the collection fits in one notebook.
- Use `_01`, `_02`, ... suffixes when the collection needs multiple notebooks.
- Reuse an existing notebook only when exactly one notebook has the target title.
- Fail instead of guessing when the Zotero collection name is ambiguous or multiple notebooks share the same title.

## Common Commands

Import all default-PDF matches in a collection:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --notebook-base "LOB_TTT"
```

Import a named paper's PDF from a collection:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --title-match "LiT: limit order book transformer" \
  --notebook-base "LOB_TTT_single"
```

Import a named item's PDF and another supported attachment type:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "SGN.300" \
  --title-match "Homework_4" \
  --extension pdf \
  --extension md \
  --notebook-base "SGN300_hw4"
```

If you request an unsupported local format such as `mlx`, the script stops immediately with a clear validation error.

Use a non-default NotebookLM profile:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --title-match "DeepLOB" \
  --notebook-base "LOB_TTT_deeplob" \
  --profile default
```

Override local Zotero paths:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --notebook-base "LOB_TTT" \
  --zotero-db ~/Zotero/zotero.sqlite \
  --zotero-storage ~/Zotero/storage
```

## Resources

- `scripts/import_zotero_to_notebooklm.py`: end-to-end importer
- `references/workflow.md`: behavior details, matching rules, and failure conditions
