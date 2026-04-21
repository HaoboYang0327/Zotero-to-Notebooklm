# Workflow Reference

## Behavior

- Read Zotero from `zotero.sqlite` with `mode=ro&immutable=1` to avoid lock contention with a running Zotero desktop app.
- Always run `nlm login --check` first.
- Launch `nlm login` automatically when the check fails, then re-check auth before continuing.
- Resolve descendant collections recursively so a parent collection can include nested folders.
- Treat local Zotero attachments as upload candidates.
- Filter candidates by requested file extension.
- Default extension filter: `pdf`.
- Reject requested extensions that are outside NotebookLM's official local-upload support list.
- Optionally narrow items by normalized title substring with `--title-match`.
- Resolve stored attachments from Zotero with:
  - `storage:<filename>` -> `<zotero_storage>/<attachment_key>/<filename>`
- Fail when an attachment path cannot be resolved to a local file.

## Notebook Rules

- Maximum per notebook: 50 files by default.
- One shard uses the base notebook name directly.
- Multiple shards use `_01`, `_02`, ... suffixes.
- Reuse an existing NotebookLM notebook when exactly one notebook matches the target title.
- Fail when multiple notebooks share the same target title.

## Duplicate Skipping

- Fetch existing NotebookLM source titles with `nlm source list <notebook-id> --json`.
- Normalize both existing source titles and candidate files by:
  - Unicode normalization
  - lowercase / casefold
  - removing punctuation boundaries
  - comparing both filename stem and full filename
- Skip the upload when any normalized candidate key already exists in the notebook.

## CLI Interface

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --notebook-base "LOB_TTT" \
  [--title-match "DeepLOB"] \
  [--extension pdf] \
  [--extension docx] \
  [--extension jpg] \
  [--extension mp3] \
  [--profile default] \
  [--max-per-notebook 50] \
  [--zotero-db ~/Zotero/zotero.sqlite] \
  [--zotero-storage ~/Zotero/storage] \
  [--wait-timeout 600]
```

## Failure Conditions

- `nlm` is missing
- interactive `nlm login` fails
- an unsupported local-upload extension is requested
- the Zotero collection name does not match exactly one collection
- a resolved notebook title matches multiple NotebookLM notebooks
- a target notebook would exceed the configured per-notebook maximum
- a requested attachment file is missing on disk
