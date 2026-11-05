---
name: docx
description: 用于创建与排版 Microsoft Word（.docx）文档。当用户需要生成正式文档、报告、带章节结构的 Word 文件，或将结构化内容导出为 .docx 时使用本技能。
compatibility: 需要主程序注册的 `render_docx_from_spec` 工具；依赖 python-docx。
---

# Word 文档（docx）技能

## 概述

本技能说明如何将**已整理好的正文内容**通过 JSON 规格交给渲染工具，生成标准 `.docx` 文件。适用于技术说明、发展历史、课程讲义等结构化文档。

## 工作流程

1. **规划**：用内置 `write_todos` 列出章节与要点（若任务较复杂）。
2. **撰稿**：根据用户主题撰写各节正文；语言与深度符合用户要求（默认中文）。
3. **规格化**：按下方 **JSON Schema** 组装字符串（合法 JSON，UTF-8 语义）。
4. **渲染**：调用工具 **`render_docx_from_spec(spec_json, output_path)`**  
   - `output_path` 使用工作区虚拟路径，例如：`/output/skills_technology_history.docx`
5. **确认**：在回复中说明生成文件的路径与文档结构摘要。

## JSON Schema（传入 `spec_json`）

根对象字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 文档总标题（用作 Word 内标题样式） |
| `sections` | array | 一级章节列表 |

每个 `section`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `heading` | string | 一级标题 |
| `paragraphs` | array of string | 该节下正文段落（每元素一个段落） |
| `subsections` | array（可选） | 二级小节 |

每个 `subsection`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `heading` | string | 二级标题 |
| `paragraphs` | array of string | 小节正文段落 |

## 写作与排版约定

- 段落文字使用 `\n` 仅当需要**同一段内换行**；通常每段单独作为 `paragraphs` 中一项。
- 避免在 JSON 中使用未转义的双引号；必要时用 `\"`。
- 发展历史类文档建议包含：背景、阶段划分、代表技术或规范、生态与工具、趋势与展望；可根据篇幅增删。

## 辅助脚本（只读参考）

目录下 `scripts/generate_docx.py` 为实际渲染实现；**不要**要求用户手动运行——一律通过 `render_docx_from_spec` 完成生成。
