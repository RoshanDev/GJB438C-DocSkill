from __future__ import annotations

from pathlib import Path
import json
import re
import shutil
import textwrap

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "gjb438c-md-first"
PKG = SKILL / "gjb438c_suite"
TESTS = SKILL / "tests"


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


# Legacy direct-template fillers are compatibility tools, not default Agent
# routes. Move them out of the default skills discovery root.
legacy_root = ROOT / "legacy-skills"
legacy_root.mkdir(exist_ok=True)
for name in ("word-fillter-438c-srs", "word-fillter-438c-sdd"):
    source = ROOT / "skills" / name
    target = legacy_root / name
    if source.exists():
        if target.exists():
            shutil.copytree(source, target, dirs_exist_ok=True)
            shutil.rmtree(source)
        else:
            shutil.move(str(source), str(target))

# Remove legacy fillers from plugin discovery metadata while preserving other
# metadata fields.
def prune_legacy(value):
    legacy = ("word-fillter-438c-srs", "word-fillter-438c-sdd")
    if isinstance(value, list):
        result = []
        for item in value:
            encoded = json.dumps(item, ensure_ascii=False) if isinstance(item, (dict, list)) else str(item)
            if any(name in encoded for name in legacy):
                continue
            result.append(prune_legacy(item))
        return result
    if isinstance(value, dict):
        return {key: prune_legacy(item) for key, item in value.items()}
    return value

for path in (ROOT / ".claude-plugin").glob("*.json"):
    data = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps(prune_legacy(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# Dynamic X/Y headings are template prototypes, not literal release headings.
profile_quality = PKG / "profile_quality.py"
text = profile_quality.read_text(encoding="utf-8")
text = re.sub(
    r"def _dynamic_heading\(value: str\) -> bool:\n(?:    .*\n)+?\n\n",
    '''def _dynamic_heading(value: str) -> bool:\n    return bool(\n        re.search(r"(?i)(?:^|[.\\s])(?:X|Y)(?=[.\\s（(]|$)", value)\n        or "唯一标识符" in value\n        or "项目唯一" in value\n    )\n\n\n''',
    text,
    count=1,
)
profile_quality.write_text(text, encoding="utf-8")

# Visible source code in CPM/SPS is real Word content. Remove fence markers,
# not the fenced payload; gjb-* blocks were already stripped separately.
volume = PKG / "volume.py"
text = volume.read_text(encoding="utf-8")
old = '''        body = re.sub(r"```.*?```", "", body, flags=re.S)\n        body = re.sub(r"!\\[[^]]*\\]\\([^)]*\\)", "", body)\n'''
new = '''        body = re.sub(r"```[^\\n]*\\n", "", body)\n        body = body.replace("```", "")\n        body = re.sub(r"!\\[[^]]*\\]\\([^)]*\\)", "", body)\n'''
if old not in text:
    raise SystemExit("volume fenced-code block not found")
volume.write_text(text.replace(old, new), encoding="utf-8")

# Replace the python-docx re-save with a direct OOXML append. This preserves the
# embedded Markdown baseline and all unknown/custom package parts exactly.
write(
    "skills/gjb438c-md-first/gjb438c_suite/evidence.py",
    r'''
    from __future__ import annotations

    from collections import defaultdict
    from pathlib import Path
    import tempfile
    from typing import Any
    from zipfile import ZIP_DEFLATED, ZipFile

    from lxml import etree

    from .markdown_doc import MarkdownDocument, parse_markdown
    from .profile_quality import artifact_kind, artifact_mapping

    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    NS = {"w": W}


    def qn(name: str) -> str:
        prefix, local = name.split(":", 1)
        if prefix != "w":
            raise ValueError(name)
        return f"{{{W}}}{local}"


    def _text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "是" if value else "否"
        if isinstance(value, dict):
            return "；".join(f"{key}={_text(item)}" for key, item in value.items())
        if isinstance(value, (list, tuple, set)):
            return "；".join(_text(item) for item in value)
        return str(value)


    def _run(value: Any, *, bold: bool = False, size: int = 21) -> etree._Element:
        run = etree.Element(qn("w:r"))
        props = etree.SubElement(run, qn("w:rPr"))
        fonts = etree.SubElement(props, qn("w:rFonts"))
        fonts.set(qn("w:ascii"), "Times New Roman")
        fonts.set(qn("w:hAnsi"), "Times New Roman")
        fonts.set(qn("w:eastAsia"), "黑体" if bold else "宋体")
        if bold:
            etree.SubElement(props, qn("w:b"))
        sz = etree.SubElement(props, qn("w:sz"))
        sz.set(qn("w:val"), str(size))
        sz_cs = etree.SubElement(props, qn("w:szCs"))
        sz_cs.set(qn("w:val"), str(size))
        text = etree.SubElement(run, qn("w:t"))
        text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        text.text = _text(value)
        return run


    def _paragraph(value: Any = "", *, bold: bool = False, size: int = 21, center: bool = False) -> etree._Element:
        paragraph = etree.Element(qn("w:p"))
        props = etree.SubElement(paragraph, qn("w:pPr"))
        spacing = etree.SubElement(props, qn("w:spacing"))
        spacing.set(qn("w:line"), "240")
        spacing.set(qn("w:lineRule"), "auto")
        if center:
            jc = etree.SubElement(props, qn("w:jc"))
            jc.set(qn("w:val"), "center")
        paragraph.append(_run(value, bold=bold, size=size))
        return paragraph


    def _page_break() -> etree._Element:
        paragraph = etree.Element(qn("w:p"))
        run = etree.SubElement(paragraph, qn("w:r"))
        br = etree.SubElement(run, qn("w:br"))
        br.set(qn("w:type"), "page")
        return paragraph


    def _cell(value: Any, *, bold: bool = False) -> etree._Element:
        cell = etree.Element(qn("w:tc"))
        props = etree.SubElement(cell, qn("w:tcPr"))
        width = etree.SubElement(props, qn("w:tcW"))
        width.set(qn("w:w"), "0")
        width.set(qn("w:type"), "auto")
        cell.append(_paragraph(value, bold=bold, size=21))
        return cell


    def _row(values: tuple[Any, ...], *, header: bool = False) -> etree._Element:
        row = etree.Element(qn("w:tr"))
        for value in values:
            row.append(_cell(value, bold=header))
        return row


    def _table(rows: list[tuple[Any, ...]]) -> etree._Element:
        table = etree.Element(qn("w:tbl"))
        props = etree.SubElement(table, qn("w:tblPr"))
        borders = etree.SubElement(props, qn("w:tblBorders"))
        for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
            node = etree.SubElement(borders, qn(f"w:{edge}"))
            node.set(qn("w:val"), "single")
            node.set(qn("w:sz"), "4")
            node.set(qn("w:space"), "0")
            node.set(qn("w:color"), "auto")
        for index, values in enumerate(rows):
            table.append(_row(values, header=index == 0))
        return table


    def append_evidence_appendix(
        docx: str | Path,
        source: str | Path | MarkdownDocument,
    ) -> Path:
        document = source if isinstance(source, MarkdownDocument) else parse_markdown(source)
        artifacts = list(getattr(document, "artifacts", ()) or ())
        target = Path(docx)
        if not artifacts:
            return target
        groups: dict[str, list[Any]] = defaultdict(list)
        for artifact in artifacts:
            groups[artifact_kind(artifact) or "unknown"].append(artifact)
        with ZipFile(target, "r") as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        root = etree.fromstring(entries["word/document.xml"])
        body = root.find("w:body", NS)
        if body is None:
            raise ValueError("DOCX 缺少 word/document.xml/w:body")
        section = body.find("w:sectPr", NS)
        insert_at = body.index(section) if section is not None else len(body)
        elements: list[etree._Element] = [
            _page_break(),
            _paragraph("结构化工程证据（机器可审计视图）", bold=True, size=24, center=True),
            _paragraph(
                "本附录将 Markdown 中的 gjb-* 证据块转换为 Word 可见内容。"
                "它用于评审、追踪和机器审计，不替代正文中的技术论证。"
            ),
        ]
        for kind in sorted(groups):
            elements.append(_paragraph(f"gjb-{kind}", bold=True, size=21))
            rows: list[tuple[Any, ...]] = [("序号", "稳定标识", "字段", "内容")]
            row_number = 0
            for artifact in groups[kind]:
                payload = artifact_mapping(artifact)
                artifact_id = str(payload.get("id", ""))
                fields = [(key, value) for key, value in payload.items() if key != "id"] or [("内容", "")]
                for field_name, value in fields:
                    row_number += 1
                    rows.append((row_number, artifact_id, field_name, _text(value)))
            elements.append(_table(rows))
        for offset, element in enumerate(elements):
            body.insert(insert_at + offset, element)
        entries["word/document.xml"] = etree.tostring(
            root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone="yes",
        )
        with tempfile.NamedTemporaryFile(
            prefix=f".{target.stem}-evidence-",
            suffix=".docx",
            dir=target.parent,
            delete=False,
        ) as handle:
            temp = Path(handle.name)
        try:
            with ZipFile(temp, "w", compression=ZIP_DEFLATED) as archive:
                for name, payload in entries.items():
                    archive.writestr(name, payload)
            temp.replace(target)
        finally:
            if temp.exists():
                temp.unlink()
        return target
    ''',
)

# Reports are committed only after all gates pass, just like the DOCX itself.
cli = PKG / "cli.py"
text = cli.read_text(encoding="utf-8")
text = text.replace(
    '''                    if args.docx_audit_json:\n                        Path(args.docx_audit_json).write_text(docx_report.to_json(), encoding="utf-8")\n                    if not docx_report.passed:\n''',
    '''                    if not docx_report.passed:\n''',
)
text = text.replace(
    '''                        if args.volume_json:\n                            volume_target = Path(args.volume_json)\n                            volume_target.parent.mkdir(parents=True, exist_ok=True)\n                            volume_target.write_text(volume_report.to_json(), encoding="utf-8")\n                        if not volume_report.passed:\n''',
    '''                        if not volume_report.passed:\n''',
)
old = '''                    os.replace(result.output, target)\n                    print(target)\n                    print(docx_report.to_text())\n'''
new = '''                    os.replace(result.output, target)\n                    if args.docx_audit_json:\n                        audit_target = Path(args.docx_audit_json)\n                        audit_target.parent.mkdir(parents=True, exist_ok=True)\n                        audit_target.write_text(docx_report.to_json(), encoding="utf-8")\n                    if args.volume_json and volume_report:\n                        volume_target = Path(args.volume_json)\n                        volume_target.parent.mkdir(parents=True, exist_ok=True)\n                        volume_target.write_text(volume_report.to_json(), encoding="utf-8")\n                    print(target)\n                    print(docx_report.to_text())\n'''
if old not in text:
    raise SystemExit("CLI atomic report insertion point not found")
cli.write_text(text.replace(old, new), encoding="utf-8")

# Suite-level identity/status consistency and per-document metadata floors.
suite = PKG / "suite.py"
text = suite.read_text(encoding="utf-8")
needle = '''        report = SuiteAuditReport(manifest_path, normalized_tier)\n        base = manifest_path.parent\n'''
replacement = '''        report = SuiteAuditReport(manifest_path, normalized_tier)\n        base = manifest_path.parent\n        if audit_profile == "release" and str(suite.get("status", "")).strip().lower() not in {\n            "approved", "released", "baseline", "已批准", "已发布", "已基线"\n        }:\n            _add(\n                report,\n                "ERROR",\n                "SUITE_NOT_APPROVED",\n                f"suite.status={suite.get('status')!r}，正式套件必须处于 approved/released/baseline 状态",\n            )\n'''
if needle not in text:
    raise SystemExit("suite status insertion point not found")
text = text.replace(needle, replacement)
needle = '''        _cross_reference_issues(report, documents)\n        computed_floor = total_floor\n'''
replacement = '''        document_ids: dict[str, str] = {}\n        software_identifiers: dict[str, str] = {}\n        for code, document in documents.items():\n            metadata_document = document.metadata.get("document")\n            document_id = (\n                str(metadata_document.get("id", "")).strip()\n                if isinstance(metadata_document, dict)\n                else ""\n            )\n            if not document_id:\n                _add(report, "ERROR", "SUITE_DOCUMENT_ID_REQUIRED", "缺少 document.id", code)\n            elif document_id in document_ids:\n                _add(\n                    report,\n                    "ERROR",\n                    "SUITE_DOCUMENT_ID_DUPLICATE",\n                    f"document.id={document_id} 已被 {document_ids[document_id]} 使用",\n                    code,\n                )\n            else:\n                document_ids[document_id] = code\n            software = document.metadata.get("software")\n            identifier = (\n                str(software.get("identifier", "")).strip()\n                if isinstance(software, dict)\n                else ""\n            )\n            if identifier:\n                software_identifiers[code] = identifier\n            quality = document.metadata.get("quality")\n            declared_floor = (\n                quality.get("min_body_pages")\n                if isinstance(quality, dict)\n                else None\n            )\n            entry = entries.get(code, {})\n            expected_floor = minimum_body_pages(\n                code, normalized_tier, entry.get("min_body_pages") if isinstance(entry, dict) else None\n            )\n            if declared_floor is None or int(declared_floor) < expected_floor:\n                _add(\n                    report,\n                    "ERROR",\n                    "SUITE_MARKDOWN_PAGE_FLOOR_MISMATCH",\n                    f"quality.min_body_pages={declared_floor!r} 低于 manifest/Profile 下限 {expected_floor}",\n                    code,\n                )\n        distinct_identifiers = set(software_identifiers.values())\n        if len(distinct_identifiers) > 1:\n            _add(\n                report,\n                "ERROR",\n                "SUITE_SOFTWARE_IDENTIFIER_INCONSISTENT",\n                "不同文档声明了不同 software.identifier："\n                + ", ".join(f"{code}={value}" for code, value in sorted(software_identifiers.items())),\n            )\n        unknown_entries = sorted(set(entries) - set(all_codes))\n        for code in unknown_entries:\n            _add(report, "ERROR", "SUITE_UNKNOWN_DOCUMENT_TYPE", "未知文档类型", code)\n        _cross_reference_issues(report, documents)\n        computed_floor = total_floor\n'''
if needle not in text:
    raise SystemExit("suite consistency insertion point not found")
suite.write_text(text.replace(needle, replacement), encoding="utf-8")

# Bundle profiles and the neutral front-matter master into wheels.
package_front = PKG / "data" / "front-matter" / "standard-front-matter.docx"
package_front.parent.mkdir(parents=True, exist_ok=True)
source_front = SKILL / "templates" / "front-matter" / "standard-front-matter.docx"
if source_front.is_file():
    shutil.copy2(source_front, package_front)
for py in PKG.glob("*.py"):
    raw = py.read_text(encoding="utf-8")
    raw = raw.replace(
        'Path(__file__).resolve().parents[1] / "templates" / "front-matter" / "standard-front-matter.docx"',
        'Path(__file__).resolve().parent / "data" / "front-matter" / "standard-front-matter.docx"',
    )
    raw = raw.replace(
        'Path(__file__).resolve().parent.parent / "templates" / "front-matter" / "standard-front-matter.docx"',
        'Path(__file__).resolve().parent / "data" / "front-matter" / "standard-front-matter.docx"',
    )
    py.write_text(raw, encoding="utf-8")
pyproject = SKILL / "pyproject.toml"
raw = pyproject.read_text(encoding="utf-8")
if "[tool.setuptools.package-data]" not in raw:
    raw += '\n[tool.setuptools.package-data]\ngjb438c_suite = ["data/**/*.yaml", "data/**/*.docx"]\n'
elif "data/**/*.docx" not in raw:
    raw = raw.replace(
        "[tool.setuptools.package-data]",
        '[tool.setuptools.package-data]\ngjb438c_suite = ["data/**/*.yaml", "data/**/*.docx"]',
        1,
    )
pyproject.write_text(raw, encoding="utf-8")

# README must describe legacy fillers as explicit compatibility paths.
readme = ROOT / "README.md"
raw = readme.read_text(encoding="utf-8")
raw = raw.replace(
    "旧的 SRS/SDD Word 填充入口暂时保留，用于兼容和回归对照。",
    "旧版 SRS/SDD 直接 Word 填充器已移至 `legacy-skills/`；只有用户明确要求绕过 Markdown、直接填充现成模板时才使用。",
)
readme.write_text(raw, encoding="utf-8")

write(
    "skills/gjb438c-md-first/tests/test_post_review_hardening.py",
    r'''
    from pathlib import Path
    import re

    from gjb438c_suite.evidence import append_evidence_appendix
    from gjb438c_suite.import_word import import_word
    from gjb438c_suite.markdown_doc import parse_markdown
    from gjb438c_suite.profile_quality import audit_profile_document
    from gjb438c_suite.render import render_document


    def test_default_skill_discovery_contains_core_plus_20_profiles_only():
        root = Path(__file__).resolve().parents[3]
        names = sorted(
            path.parent.name
            for path in (root / "skills").glob("*/SKILL.md")
            if path.parent.name.startswith("gjb438c-")
        )
        assert len(names) == 21
        assert "gjb438c-md-first" in names
        assert not (root / "skills/word-fillter-438c-srs").exists()
        assert not (root / "skills/word-fillter-438c-sdd").exists()
        assert (root / "legacy-skills/word-fillter-438c-srs/SKILL.md").is_file()
        assert (root / "legacy-skills/word-fillter-438c-sdd/SKILL.md").is_file()


    def test_dynamic_profile_prototypes_are_not_required_literal_headings(tmp_path: Path):
        source = tmp_path / "STD.md"
        source.write_text(
            """---
    document:
      type: STD
      id: TEST-STD
      status: draft
    quality:
      tier: prototype
      fixture: true
    software:
      name: 示例软件
      identifier: TEST
      version: V1.0
    sources:
      - id: SRC-1
        title: 示例来源
    ---
    # 1 范围
    # 2 引用文档
    # 3 测试准备
    ## 3.1 功能测试准备
    ### 3.1.1 硬件准备
    ### 3.1.2 软件准备
    ### 3.1.3 其他测试前准备
    # 4 测试说明
    ## 4.1 虚拟机测试
    ### 4.1.1 创建虚拟机
    # 5 需求的可追踪性
    # 6 注释
    """,
            encoding="utf-8",
        )
        report = audit_profile_document(
            source,
            document_type="STD",
            audit_profile="draft",
            tier="prototype",
        )
        assert not any("3.X" in item.message or "4.X" in item.message for item in report.issues)


    def test_ooxml_evidence_append_preserves_exact_markdown_roundtrip(tmp_path: Path):
        source = Path(__file__).resolve().parents[1] / "examples/SRS.example.md"
        docx = tmp_path / "SRS.docx"
        returned = tmp_path / "SRS.returned.md"
        render_document(source, docx, profile="draft")
        append_evidence_appendix(docx, parse_markdown(source))
        result = import_word(docx, returned)
        assert result.exact_round_trip
        assert returned.read_bytes() == source.read_bytes()


    def test_non_gjb_fenced_code_counts_as_visible_content(tmp_path: Path):
        source = tmp_path / "CPM.md"
        source.write_text(
            """---
    document:
      type: CPM
      id: TEST-CPM
    quality:
      tier: prototype
      fixture: true
    ---
    # 1 范围

    ```go
    package main
    func main() { println("visible code") }
    ```
    """,
            encoding="utf-8",
        )
        from gjb438c_suite.volume import visible_markdown_characters
        assert visible_markdown_characters(parse_markdown(source)) > 30
    ''',
)

# Extend CI with wheel isolation and exact skill-layout checks.
workflow = ROOT / ".github/workflows/gjb438c-md-first.yml"
raw = workflow.read_text(encoding="utf-8")
needle = '''          - name: Verify all 20 profiles are standalone\n            run: |\n'''
insert = '''          - name: Verify wheel is self-contained outside the repository\n            run: |\n              python -m pip install build\n              python -m build --wheel skills/gjb438c-md-first --outdir /tmp/gjb438c-wheel\n              python -m venv /tmp/gjb438c-wheel-venv\n              /tmp/gjb438c-wheel-venv/bin/pip install /tmp/gjb438c-wheel/*.whl\n              cd /tmp\n              /tmp/gjb438c-wheel-venv/bin/gjb438c profile --type SSS --json > /tmp/wheel-SSS.json\n              /tmp/gjb438c-wheel-venv/bin/gjb438c init --type STD --output /tmp/wheel-STD.md\n              test -s /tmp/wheel-STD.md\n          - name: Verify default skill discovery layout\n            run: |\n              test "$(find skills -mindepth 2 -maxdepth 2 -name SKILL.md -path 'skills/gjb438c-*/*' | wc -l)" -eq 21\n              test ! -e skills/word-fillter-438c-srs\n              test ! -e skills/word-fillter-438c-sdd\n              test -f legacy-skills/word-fillter-438c-srs/SKILL.md\n              test -f legacy-skills/word-fillter-438c-sdd/SKILL.md\n          - name: Verify all 20 profiles are standalone\n            run: |\n'''
if needle not in raw:
    raise SystemExit("CI standalone step not found")
workflow.write_text(raw.replace(needle, insert), encoding="utf-8")

print("post-review hardening applied")
