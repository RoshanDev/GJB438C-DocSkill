#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

from gjb438c_suite.markdown_doc import extract_template_outline, parse_markdown, render_skeleton
from gjb438c_suite.registry import default_template_root, iter_document_types, resolve_template


def main() -> int:
    parser = argparse.ArgumentParser(description="验证二十份 GJB 438C 模板都能生成 Markdown 骨架")
    parser.add_argument("--template-root", type=Path, default=default_template_root())
    args = parser.parse_args()

    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gjb438c-template-smoke-") as temp_name:
        temp = Path(temp_name)
        for item in iter_document_types():
            try:
                template = resolve_template(item, args.template_root)
                outline = extract_template_outline(template)
                if not any(heading.level == 1 for heading in outline):
                    raise ValueError("没有一级标题")
                markdown = render_skeleton(document_type=item, outline=outline)
                output = temp / f"{item.number:02d}-{item.code}.md"
                output.write_text(markdown, encoding="utf-8")
                parsed = parse_markdown(output)
                if parsed.parse_errors:
                    raise ValueError("；".join(parsed.parse_errors))
                print(f"PASS {item.number:02d} {item.code:<4} headings={len(outline)} template={template.name}")
            except Exception as exc:  # noqa: BLE001 - smoke script reports all failures
                failures.append(f"{item.code}: {exc}")
                print(f"FAIL {item.code}: {exc}")
    if failures:
        raise SystemExit("模板冒烟失败：\n" + "\n".join(failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
