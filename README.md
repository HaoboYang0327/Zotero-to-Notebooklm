# Zotero to NotebookLM

A Codex skill for importing local Zotero attachments into NotebookLM through `notebooklm-mcp-cli` (`nlm`).

It is designed for workflows like:
- find a paper in a Zotero collection by title and upload its PDF into a NotebookLM notebook
- import all supported files from a Zotero collection into NotebookLM
- reuse existing notebooks, skip duplicate uploads, and shard at 50 sources per notebook
- auto-run `nlm login` when the NotebookLM session is missing or expired

## What It Supports

The importer reads local attachments from Zotero and only accepts NotebookLM-supported local upload formats.

Supported local extensions currently include:
- Documents: `pdf`, `docx`, `txt`, `md`, `csv`, `pptx`, `epub`
- Images: `avif`, `bmp`, `gif`, `heic`, `heif`, `ico`, `jp2`, `jpe`, `jpeg`, `jpg`, `png`, `tif`, `tiff`, `webp`
- Audio / media: `3g2`, `3gp`, `aac`, `aif`, `aifc`, `aiff`, `amr`, `au`, `avi`, `cda`, `m4a`, `mid`, `mp3`, `mp4`, `mpeg`, `ogg`, `opus`, `ra`, `ram`, `snd`, `wav`, `wma`

Unsupported extensions such as `mlx` are rejected locally before upload.

## Requirements

- Zotero local data, typically:
  - `~/Zotero/zotero.sqlite`
  - `~/Zotero/storage`
- `uv`
- `notebooklm-mcp-cli`

Install `nlm` if needed:

```bash
uv tool install notebooklm-mcp-cli
```

## Install the Skill

Clone or copy this repository into your Codex skills directory:

```bash
git clone https://github.com/HaoboYang0327/Zotero-to-Notebooklm.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/notebooklm-zotero-import"
```

Or copy these files manually into:

```bash
${CODEX_HOME:-$HOME/.codex}/skills/notebooklm-zotero-import
```

The skill entrypoint is:

```bash
scripts/import_zotero_to_notebooklm.py
```

## Usage

Import all PDFs from a Zotero collection:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --notebook-base "LOB_TTT"
```

Import a single paper by title:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --title-match "LiT: limit order book transformer" \
  --notebook-base "LOB_TTT_single"
```

Import selected supported formats:

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "SGN.300" \
  --title-match "Homework_4" \
  --extension pdf \
  --extension md \
  --notebook-base "SGN300_hw4"
```

## Behavior

- Runs `nlm login --check` before every import
- Launches `nlm login` automatically if the session is invalid
- Searches Zotero collections recursively
- Filters items by normalized title substring when `--title-match` is provided
- Reuses an existing same-name notebook when it is unique
- Skips files already present in the target notebook
- Splits imports into notebook shards with a default cap of 50 sources per notebook

## Repository Contents

- `SKILL.md`: Codex skill instructions
- `agents/openai.yaml`: Codex skill interface metadata
- `scripts/import_zotero_to_notebooklm.py`: importer implementation
- `references/workflow.md`: workflow reference
- `README.md`: English usage guide
- `README.zh-CN.md`: Chinese usage guide
