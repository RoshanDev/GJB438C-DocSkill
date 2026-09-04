from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Sequence

import yaml

from .audit_docx import audit_docx
from .front_matter import FrontMatterError, load_payload, render_front_matter
from .finalize import FinalizeError, refresh_toc_cache
from .import_word import ImportWordError, import_word
from .markdown_doc import extract_template_outline, render_skeleton
from .quality import audit_markdown
from .registry import get_document_type, iter_document_types, resolve_template
from .render import RenderError, render_document


def _load_mapping(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    value = json.loads(text) if source.suffix.lower() == ".json" else yaml.safe_load(text)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{source} 必须是 JSON/YAML 对象")
    return value


def _write_report(report, output: str | None) -> None:
    if output:
        Path(output).write_text(report.to_json(), encoding="utf-8")
    print(report.to_text())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gjb438c", description="GJB 438C Markdown-first 文档工程")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出 20 类 GJB 438C 文档")

    init = sub.add_parser("init", help="从对应 DOCX 模板目录创建 Markdown 骨架")
    init.add_argument("--type", required=True)
    init.add_argument("--template-root")
    init.add_argument("--project", help="项目元数据 JSON/YAML")
    init.add_argument("--output", required=True)

    audit = sub.add_parser("audit", help="审核 Markdown 内容和结构化证据")
    audit.add_argument("input")
    audit.add_argument("--profile", choices=["draft", "review", "release"], default="review")
    audit.add_argument("--type")
    audit.add_argument("--baseline-srs")
    audit.add_argument("--json")

    render = sub.add_parser("render", help="审核通过后将 Markdown 生成 DOCX")
    render.add_argument("input")
    render.add_argument("--output", required=True)
    render.add_argument("--profile", choices=["draft", "review", "release"], default="review")
    render.add_argument("--baseline-srs")
    render.add_argument("--front-template")
    render.add_argument("--docx-audit-json")
    render.add_argument(
        "--refresh-toc",
        action="store_true",
        help="使用 LibreOffice 生成可见目录缓存，但只回填 TOC 结果，不让 LibreOffice 改写其它 OOXML",
    )

    finalize = sub.add_parser("refresh-toc", help="刷新 DOCX 的可见目录缓存")
    finalize.add_argument("input")
    finalize.add_argument("--output")
    finalize.add_argument("--audit-json")

    imp = sub.add_parser("import-word", help="将生成后的 Word 回流为 Markdown")
    imp.add_argument("input")
    imp.add_argument("--output", required=True)

    docx_audit = sub.add_parser("audit-docx", help="审核 DOCX 字体、字号、字段和结构")
    docx_audit.add_argument("input")
    docx_audit.add_argument("--profile", choices=["review", "release"], default="review")
    docx_audit.add_argument("--json")

    front = sub.add_parser("front-matter", help="单独填充统一前三页")
    front.add_argument("--template", required=True)
    front.add_argument("--data", required=True)
    front.add_argument("--output", required=True)
    front.add_argument("--release", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            for item in iter_document_types():
                print(f"{item.number:02d} {item.code:<4} {item.chinese_name} {item.clause} 附录{item.appendix}")
            return 0

        if args.command == "init":
            template = resolve_template(args.type, Path(args.template_root) if args.template_root else None)
            item = get_document_type(args.type)
            outline = extract_template_outline(template)
            project = _load_mapping(args.project)
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                render_skeleton(document_type=item, outline=outline, project=project),
                encoding="utf-8",
            )
            print(output)
            return 0

        if args.command == "audit":
            report = audit_markdown(
                args.input,
                profile=args.profile,
                document_type=args.type,
                baseline_srs=args.baseline_srs,
            )
            _write_report(report, args.json)
            return 0 if report.passed else 2

        if args.command == "render":
            result = render_document(
                args.input,
                args.output,
                profile=args.profile,
                baseline_srs=args.baseline_srs,
                front_template=args.front_template,
            )
            if args.refresh_toc:
                refresh_toc_cache(result.output)
            report = audit_docx(result.output, profile="release" if args.profile == "release" else "review")
            if args.docx_audit_json:
                Path(args.docx_audit_json).write_text(report.to_json(), encoding="utf-8")
            print(result.output)
            print(report.to_text())
            return 0 if report.passed else 3

        if args.command == "refresh-toc":
            output = refresh_toc_cache(args.input, args.output)
            report = audit_docx(output, profile="release")
            if args.audit_json:
                Path(args.audit_json).write_text(report.to_json(), encoding="utf-8")
            print(output)
            print(report.to_text())
            return 0 if report.passed else 3

        if args.command == "import-word":
            result = import_word(args.input, args.output)
            print(result.output)
            print("exact-round-trip" if result.exact_round_trip else result.warning)
            return 0

        if args.command == "audit-docx":
            report = audit_docx(args.input, profile=args.profile)
            _write_report(report, args.json)
            return 0 if report.passed else 3

        if args.command == "front-matter":
            payload = load_payload(args.data)
            output = render_front_matter(args.template, payload, args.output, release=args.release)
            print(output)
            return 0

        parser.error(f"未知命令：{args.command}")
        return 2
    except (ValueError, FileNotFoundError, FrontMatterError, RenderError, ImportWordError, FinalizeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
