# Zotero to NotebookLM

这是一个 Codex skill，用来通过 `notebooklm-mcp-cli` 的 `nlm` 命令，把本地 Zotero 附件导入到 NotebookLM。

它适合下面这类任务：
- 在 Zotero 某个 collection 中按标题找到论文，并把它的 PDF 上传到指定 NotebookLM notebook
- 把某个 Zotero collection 中的所有受支持文件导入 NotebookLM
- 复用已有 notebook、跳过重复来源，并把每个 notebook 控制在 50 个 source 以内
- 当 NotebookLM 登录失效时，自动执行 `nlm login`

## 支持范围

导入脚本读取 Zotero 本地附件，并且只允许 NotebookLM 官方支持的本地上传格式。

当前支持的本地扩展名包括：
- 文档类：`pdf`, `docx`, `txt`, `md`, `csv`, `pptx`, `epub`
- 图片类：`avif`, `bmp`, `gif`, `heic`, `heif`, `ico`, `jp2`, `jpe`, `jpeg`, `jpg`, `png`, `tif`, `tiff`, `webp`
- 音频 / 媒体类：`3g2`, `3gp`, `aac`, `aif`, `aifc`, `aiff`, `amr`, `au`, `avi`, `cda`, `m4a`, `mid`, `mp3`, `mp4`, `mpeg`, `ogg`, `opus`, `ra`, `ram`, `snd`, `wav`, `wma`

像 `mlx` 这样的不支持格式，会在本地直接报错，不会等到上传阶段才失败。

## 环境要求

- 本地 Zotero 数据，通常是：
  - `~/Zotero/zotero.sqlite`
  - `~/Zotero/storage`
- `uv`
- `notebooklm-mcp-cli`

如果还没有安装 `nlm`：

```bash
uv tool install notebooklm-mcp-cli
```

## 安装方式

把这个仓库克隆到 Codex 的 skills 目录：

```bash
git clone https://github.com/HaoboYang0327/Zotero-to-Notebooklm.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/notebooklm-zotero-import"
```

也可以手动把这些文件复制到：

```bash
${CODEX_HOME:-$HOME/.codex}/skills/notebooklm-zotero-import
```

这个 skill 的入口脚本是：

```bash
scripts/import_zotero_to_notebooklm.py
```

## 使用示例

导入某个 collection 下的全部 PDF：

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --notebook-base "LOB_TTT"
```

按标题只导入单篇论文：

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "Limit Order Book" \
  --title-match "LiT: limit order book transformer" \
  --notebook-base "LOB_TTT_single"
```

导入某个条目下的指定受支持格式：

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "SGN.300" \
  --title-match "Homework_4" \
  --extension pdf \
  --extension md \
  --notebook-base "SGN300_hw4"
```

## 行为说明

- 每次导入前都会执行 `nlm login --check`
- 如果登录状态失效，会自动启动 `nlm login`
- 会递归搜索 Zotero collection 及其子 collection
- 如果传入 `--title-match`，会按规范化后的标题子串进行匹配
- 如果目标 notebook 同名且唯一，则直接复用
- 如果目标 notebook 里已经存在同名来源，则自动跳过
- 默认每个 notebook 最多导入 50 个 source，超过后自动拆分为 `_01`、`_02` 等分卷

## 仓库内容

- `SKILL.md`：Codex skill 指令
- `agents/openai.yaml`：Codex skill 接口元数据
- `scripts/import_zotero_to_notebooklm.py`：导入脚本
- `references/workflow.md`：流程说明
- `README.md`：英文说明
- `README.zh-CN.md`：中文说明
