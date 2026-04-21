# Zotero to NotebookLM

An independent Codex skill for moving local Zotero attachments into NotebookLM through `nlm`.

This repository documents the skill itself. It does not bundle or reproduce the upstream `notebooklm-mcp-cli` project. Install that dependency separately and refer to its repository for its own documentation, license, and implementation details.

Upstream dependency repository:
- `notebooklm-mcp-cli`: https://github.com/jacob-bd/notebooklm-mcp-cli

## What This Skill Does

- reads local Zotero metadata from `zotero.sqlite`
- resolves attachment files from the Zotero storage directory
- filters items by collection, optional title match, and allowed file extensions
- checks NotebookLM login state before every run
- creates or reuses NotebookLM notebooks
- skips files that are already present in the target notebook
- splits uploads into multiple notebooks when a notebook would exceed 50 sources

## Supported Local Upload Formats

The skill only allows file extensions that NotebookLM currently supports for local upload.

- Documents: `pdf`, `docx`, `txt`, `md`, `csv`, `pptx`, `epub`
- Images: `avif`, `bmp`, `gif`, `heic`, `heif`, `ico`, `jp2`, `jpe`, `jpeg`, `jpg`, `png`, `tif`, `tiff`, `webp`
- Audio and media: `3g2`, `3gp`, `aac`, `aif`, `aifc`, `aiff`, `amr`, `au`, `avi`, `cda`, `m4a`, `mid`, `mp3`, `mp4`, `mpeg`, `ogg`, `opus`, `ra`, `ram`, `snd`, `wav`, `wma`

Unsupported extensions are rejected locally before upload.

## Requirements

- local Zotero data
- `uv`
- `notebooklm-mcp-cli`
- a Chromium-based browser available for `nlm login` when authentication is needed

Install the dependency:

```bash
uv tool install notebooklm-mcp-cli
```

## Install the Skill

Clone this repository into your Codex skills directory:

```bash
git clone https://github.com/HaoboYang0327/Zotero-to-Notebooklm.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/notebooklm-zotero-import"
```

The main entrypoint is:

```bash
scripts/import_zotero_to_notebooklm.py
```

## Usage

Import all default-PDF attachments from a Zotero collection:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --notebook-base "<NOTEBOOK_NAME>"
```

Import only attachments whose Zotero item title matches a phrase:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --title-match "<TITLE_SUBSTRING>" \
  --notebook-base "<NOTEBOOK_NAME>"
```

Import selected supported extensions:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --title-match "<TITLE_SUBSTRING>" \
  --extension pdf \
  --extension md \
  --notebook-base "<NOTEBOOK_NAME>"
```

Override Zotero paths or the NotebookLM profile when needed:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --notebook-base "<NOTEBOOK_NAME>" \
  --profile "<NLM_PROFILE>" \
  --zotero-db "<PATH_TO_ZOTERO_SQLITE>" \
  --zotero-storage "<PATH_TO_ZOTERO_STORAGE>"
```

## Authentication Behavior

Each run starts with `nlm login --check`.

- If the session is valid, the skill continues without opening a login flow.
- If the session is missing or expired, the current implementation launches `nlm login` automatically.

## Repository Layout

- `SKILL.md`: Codex skill instructions
- `agents/openai.yaml`: skill interface metadata
- `scripts/import_zotero_to_notebooklm.py`: importer implementation
- `references/workflow.md`: workflow notes and constraints
- `README.md`: English overview
- `README.zh-CN.md`: Chinese overview
