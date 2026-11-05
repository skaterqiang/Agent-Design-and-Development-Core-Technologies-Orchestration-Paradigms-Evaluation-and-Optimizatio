"""从 JSON 规格生成 .docx（供 DeepAgent 工具通过子进程调用）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH


def build_document(spec: dict) -> Document:
    doc = Document()
    title = spec.get("title") or "未命名文档"
    h0 = doc.add_heading(title, level=0)
    h0.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for section in spec.get("sections", []):
        doc.add_heading(section.get("heading", ""), level=1)
        for line in section.get("paragraphs", []):
            if line:
                doc.add_paragraph(str(line))
        for sub in section.get("subsections", []):
            doc.add_heading(sub.get("heading", ""), level=2)
            for line in sub.get("paragraphs", []):
                if line:
                    doc.add_paragraph(str(line))
    return doc


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python generate_docx.py <spec.json> <output.docx>", file=sys.stderr)
        sys.exit(2)
    spec_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    build_document(spec).save(str(out_path))


if __name__ == "__main__":
    main()
