# Zotero to NotebookLM

这是一个独立的 Codex skill，用来通过 `nlm` 把本地 Zotero 附件导入到 NotebookLM。

这个仓库只描述这个 skill 本身，不打包也不复述上游 `notebooklm-mcp-cli` 项目的实现或文档内容。`notebooklm-mcp-cli` 需要单独安装；它自身的文档、许可证和实现细节请以其上游仓库为准。

## 这个 Skill 做什么

- 从 `zotero.sqlite` 读取本地 Zotero 元数据
- 从 Zotero storage 目录解析真实附件文件
- 按 collection、可选标题匹配、可选扩展名过滤候选文件
- 每次运行前检查 NotebookLM 登录状态
- 创建或复用 NotebookLM notebook
- 自动跳过目标 notebook 中已经存在的文件
- 当单个 notebook 会超过 50 个 source 时自动拆分

## 支持的本地上传格式

这个 skill 只允许 NotebookLM 当前官方支持的本地上传扩展名。

- 文档类：`pdf`, `docx`, `txt`, `md`, `csv`, `pptx`, `epub`
- 图片类：`avif`, `bmp`, `gif`, `heic`, `heif`, `ico`, `jp2`, `jpe`, `jpeg`, `jpg`, `png`, `tif`, `tiff`, `webp`
- 音频与媒体：`3g2`, `3gp`, `aac`, `aif`, `aifc`, `aiff`, `amr`, `au`, `avi`, `cda`, `m4a`, `mid`, `mp3`, `mp4`, `mpeg`, `ogg`, `opus`, `ra`, `ram`, `snd`, `wav`, `wma`

不支持的扩展名会在本地直接报错，不会进入上传阶段。

## 依赖要求

- 本地 Zotero 数据
- `uv`
- `notebooklm-mcp-cli`
- 当需要重新认证时，可供 `nlm login` 使用的 Chromium 系浏览器

安装依赖：

```bash
uv tool install notebooklm-mcp-cli
```

## 安装 Skill

把这个仓库克隆到 Codex 的 skills 目录：

```bash
git clone https://github.com/HaoboYang0327/Zotero-to-Notebooklm.git \
  "${CODEX_HOME:-$HOME/.codex}/skills/notebooklm-zotero-import"
```

主入口脚本：

```bash
scripts/import_zotero_to_notebooklm.py
```

## 使用方式

导入某个 Zotero collection 中默认的 PDF 附件：

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --notebook-base "<NOTEBOOK_NAME>"
```

只导入标题包含指定短语的附件：

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --title-match "<TITLE_SUBSTRING>" \
  --notebook-base "<NOTEBOOK_NAME>"
```

导入指定的受支持扩展名：

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --title-match "<TITLE_SUBSTRING>" \
  --extension pdf \
  --extension md \
  --notebook-base "<NOTEBOOK_NAME>"
```

需要时可以覆盖 Zotero 路径或 NotebookLM profile：

```bash
uv run ~/.codex/skills/notebooklm-zotero-import/scripts/import_zotero_to_notebooklm.py \
  --collection "<ZOTERO_COLLECTION>" \
  --notebook-base "<NOTEBOOK_NAME>" \
  --profile "<NLM_PROFILE>" \
  --zotero-db "<PATH_TO_ZOTERO_SQLITE>" \
  --zotero-storage "<PATH_TO_ZOTERO_STORAGE>"
```

## 认证行为

每次运行都会先执行 `nlm login --check`。

- 如果当前会话有效，skill 会直接继续，不会打开登录流程。
- 如果当前会话失效或不存在，当前实现会自动启动 `nlm login`。

## 仓库结构

- `SKILL.md`：Codex skill 指令
- `agents/openai.yaml`：skill 接口元数据
- `scripts/import_zotero_to_notebooklm.py`：导入脚本
- `references/workflow.md`：流程说明与约束
- `README.md`：英文说明
- `README.zh-CN.md`：中文说明
