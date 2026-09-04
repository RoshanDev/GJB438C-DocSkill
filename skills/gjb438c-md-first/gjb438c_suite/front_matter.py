"""Render the normalized standard cover/signature/revision DOCX master.

The master deliberately keeps the official visible anchors instead of long
``{{placeholder}}`` strings. Long placeholders change line wrapping and can
silently destroy the three-page layout. This module fills the known table
coordinates and exact text anchors while preserving all original formatting.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping, Sequence
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W}


def qn(local: str) -> str:
    return f"{{{W}}}{local}"


class FrontMatterError(RuntimeError):
    """Raised when the master contract or input data is invalid."""


@dataclass(frozen=True, slots=True)
class FieldLimit:
    name: str
    max_display_width: int


# Conservative limits keep the official layout stable. CJK characters count as
# two units; Latin digits/letters count as one. Callers may shorten identifiers
# or use an approved revised house template rather than silently shrinking fonts.
FIELD_LIMITS = (
    FieldLimit("archive_id", 28),
    FieldLimit("classification", 12),
    FieldLimit("project_code", 18),
    FieldLimit("document_id", 26),
    FieldLimit("phase", 12),
    FieldLimit("document_version", 14),
    FieldLimit("software_name", 28),
    FieldLimit("document_title", 28),
    FieldLimit("organization", 44),
    FieldLimit("date_cn", 24),
)

SIGNATURE_ROLES = {
    "编制：": "prepared",
    "审核：": "reviewed",
    "标审：": "standard_reviewed",
    "会签：": "countersigned",
    "批准：": "approved",
}


def _display_width(value: str) -> int:
    return sum(2 if ord(char) > 127 else 1 for char in value)


def _require_text(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if value is None:
        raise FrontMatterError(f"缺少字段：{key}")
    text = str(value).strip()
    if not text:
        raise FrontMatterError(f"字段不能为空：{key}")
    return text


def validate_payload(data: Mapping[str, Any], *, release: bool = False) -> None:
    required = [
        "archive_id",
        "project_code",
        "document_id",
        "phase",
        "document_version",
        "software_name",
        "document_title",
        "organization",
        "date_cn",
    ]
    if release:
        required.append("classification")
    for key in required:
        _require_text(data, key)

    for limit in FIELD_LIMITS:
        value = str(data.get(limit.name, "")).strip()
        if value and _display_width(value) > limit.max_display_width:
            raise FrontMatterError(
                f"字段 {limit.name} 过长（显示宽度 {_display_width(value)} > "
                f"{limit.max_display_width}），会破坏统一前三页固定版式"
            )

    signatures = data.get("signatures", {})
    if signatures is not None and not isinstance(signatures, Mapping):
        raise FrontMatterError("signatures 必须是对象")
    revisions = data.get("revisions", [])
    if not isinstance(revisions, Sequence) or isinstance(revisions, (str, bytes)):
        raise FrontMatterError("revisions 必须是数组")
    for index, revision in enumerate(revisions, 1):
        if not isinstance(revision, Mapping):
            raise FrontMatterError(f"revisions[{index}] 必须是对象")
        for key in ("date", "version", "description", "author"):
            if release and not str(revision.get(key, "")).strip():
                raise FrontMatterError(f"revisions[{index}].{key} 不能为空")


def load_payload(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:  # pragma: no cover - environment dependent
            raise FrontMatterError("读取 YAML 需要安装 PyYAML") from exc
        value = yaml.safe_load(text)
    else:
        value = json.loads(text)
    if not isinstance(value, dict):
        raise FrontMatterError("前三页数据文件必须是对象")
    return value


def _paragraph_text(paragraph: etree._Element) -> str:
    return "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))


def _set_run_text(run: etree._Element, value: str) -> None:
    text_nodes = run.findall("./w:t", NS)
    if text_nodes:
        target = text_nodes[0]
        for node in text_nodes[1:]:
            run.remove(node)
    else:
        target = etree.SubElement(run, qn("t"))
    target.set(f"{{{XML}}}space", "preserve")
    target.text = value


def _set_paragraph_text(paragraph: etree._Element, value: str) -> None:
    first_run = paragraph.find("./w:r", NS)
    run_properties = None
    if first_run is not None:
        run_properties = first_run.find("./w:rPr", NS)
    if run_properties is None:
        run_properties = paragraph.find("./w:pPr/w:rPr", NS)

    for child in list(paragraph):
        if child.tag != qn("pPr"):
            paragraph.remove(child)
    run = etree.SubElement(paragraph, qn("r"))
    if run_properties is not None:
        run.append(deepcopy(run_properties))
    _set_run_text(run, value)


def _set_cell_text(cell: etree._Element, value: str) -> None:
    paragraphs = cell.findall("./w:p", NS)
    if not paragraphs:
        paragraph = etree.SubElement(cell, qn("p"))
    else:
        paragraph = paragraphs[0]
        for extra in paragraphs[1:]:
            cell.remove(extra)
    _set_paragraph_text(paragraph, value)


def _replace_text_nodes(root: etree._Element, old: str, new: str, expected: int) -> None:
    count = 0
    for node in root.xpath(".//w:t", namespaces=NS):
        if node.text and old in node.text:
            node.text = node.text.replace(old, new)
            count += 1
    if count != expected:
        raise FrontMatterError(
            f"母版锚点 {old!r} 命中 {count} 次，期望 {expected} 次；拒绝猜测模板结构"
        )


def _signature_slot(value: Any, width: int) -> str:
    text = str(value or "").strip()
    # Preserve a visible underline even for unsigned documents.
    remaining = max(width - _display_width(text), 2)
    left = remaining // 2
    right = remaining - left
    return " " * left + text + " " * right


def _fill_signature_line(paragraph: etree._Element, name: Any, date: Any) -> None:
    underlined = [
        run
        for run in paragraph.findall("./w:r", NS)
        if run.find("./w:rPr/w:u", NS) is not None
    ]
    if len(underlined) != 2:
        raise FrontMatterError(
            f"签字行格式异常：{_paragraph_text(paragraph)!r}，应包含两个下划线槽位"
        )
    _set_run_text(underlined[0], _signature_slot(name, 12))
    _set_run_text(underlined[1], _signature_slot(date, 14))


def _top_level_tables(body: etree._Element) -> list[etree._Element]:
    return [child for child in body if child.tag == qn("tbl")]


def _fill_metadata_table(cover_table: etree._Element, data: Mapping[str, Any]) -> None:
    nested_tables = cover_table.xpath("./w:tr[1]/w:tc[2]/w:tbl", namespaces=NS)
    if len(nested_tables) != 1:
        raise FrontMatterError(f"封面右上元数据表命中 {len(nested_tables)} 次，期望 1 次")
    rows = nested_tables[0].findall("./w:tr", NS)
    values = [
        str(data.get("classification", "")).strip(),
        _require_text(data, "project_code"),
        _require_text(data, "document_id"),
        _require_text(data, "phase"),
        _require_text(data, "document_version"),
    ]
    if len(rows) != len(values):
        raise FrontMatterError(f"封面元数据表有 {len(rows)} 行，期望 5 行")
    for row, value in zip(rows, values, strict=True):
        cells = row.findall("./w:tc", NS)
        if len(cells) != 2:
            raise FrontMatterError("封面元数据表必须为两列")
        _set_cell_text(cells[1], value)


def _fill_signatures(cover_table: etree._Element, data: Mapping[str, Any]) -> None:
    signatures = data.get("signatures", {}) or {}
    if not isinstance(signatures, Mapping):
        raise FrontMatterError("signatures 必须是对象")
    found: set[str] = set()
    for paragraph in cover_table.xpath(".//w:p", namespaces=NS):
        current = _paragraph_text(paragraph).strip()
        for prefix, key in SIGNATURE_ROLES.items():
            if not current.startswith(prefix):
                continue
            entry = signatures.get(key, {}) or {}
            if not isinstance(entry, Mapping):
                raise FrontMatterError(f"signatures.{key} 必须是对象")
            _fill_signature_line(paragraph, entry.get("name"), entry.get("date"))
            found.add(key)
    missing = set(SIGNATURE_ROLES.values()) - found
    if missing:
        raise FrontMatterError(f"母版缺少签字角色：{sorted(missing)}")


def _fill_revisions(revision_table: etree._Element, data: Mapping[str, Any]) -> None:
    rows = revision_table.findall("./w:tr", NS)
    if len(rows) < 2:
        raise FrontMatterError("变更履历表至少应包含表头和一行数据")
    revisions = list(data.get("revisions", []) or [])
    prototype = rows[-1]
    while len(rows) - 1 < len(revisions):
        clone = deepcopy(prototype)
        revision_table.append(clone)
        rows.append(clone)

    for index, row in enumerate(rows[1:]):
        cells = row.findall("./w:tc", NS)
        if len(cells) != 4:
            raise FrontMatterError("变更履历表必须为四列")
        if index < len(revisions):
            revision = revisions[index]
            values = [
                str(revision.get("date", "")).strip(),
                str(revision.get("version", "")).strip(),
                str(revision.get("description", "")).strip(),
                str(revision.get("author", "")).strip(),
            ]
        else:
            values = ["", "", "", ""]
        for cell, value in zip(cells, values, strict=True):
            _set_cell_text(cell, value)


def render_front_matter(
    template: str | Path,
    data: Mapping[str, Any],
    output: str | Path,
    *,
    release: bool = False,
) -> Path:
    """Fill the three-page master without changing its layout contract."""
    validate_payload(data, release=release)
    template_path = Path(template)
    output_path = Path(output)
    if not template_path.is_file():
        raise FrontMatterError(f"找不到前三页母版：{template_path}")

    with tempfile.TemporaryDirectory(prefix="gjb438c-front-matter-") as temp_name:
        temp = Path(temp_name)
        with ZipFile(template_path) as archive:
            archive.extractall(temp)

        document_path = temp / "word" / "document.xml"
        tree = etree.parse(str(document_path))
        root = tree.getroot()
        body = root.find("./w:body", NS)
        if body is None:
            raise FrontMatterError("母版缺少 document body")
        tables = _top_level_tables(body)
        if len(tables) != 2:
            raise FrontMatterError(f"母版顶层表格数为 {len(tables)}，期望 2")
        cover_table, revision_table = tables
        if len(cover_table.findall("./w:tr", NS)) != 5:
            raise FrontMatterError("封面/签字页主表必须为 5 行")

        _replace_text_nodes(
            root,
            "档案编号：",
            f"档案编号：{_require_text(data, 'archive_id')}",
            2,
        )
        _replace_text_nodes(root, "XXXXXX", _require_text(data, "software_name"), 2)
        _replace_text_nodes(root, "软件部署手册", _require_text(data, "document_title"), 2)
        _replace_text_nodes(
            root,
            "编制单位",
            _require_text(data, "organization"),
            1,
        )
        _replace_text_nodes(root, "二○   年  月", _require_text(data, "date_cn"), 1)
        _fill_metadata_table(cover_table, data)
        _fill_signatures(cover_table, data)
        _fill_revisions(revision_table, data)

        settings_path = temp / "word" / "settings.xml"
        settings_tree = etree.parse(str(settings_path))
        settings_root = settings_tree.getroot()
        update_fields = settings_root.find("./w:updateFields", NS)
        if update_fields is None:
            update_fields = etree.SubElement(settings_root, qn("updateFields"))
        update_fields.set(qn("val"), "true")
        settings_tree.write(
            str(settings_path), xml_declaration=True, encoding="UTF-8", standalone="yes"
        )
        tree.write(
            str(document_path), xml_declaration=True, encoding="UTF-8", standalone="yes"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output_path, "w", ZIP_DEFLATED) as archive:
            for file in temp.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(temp).as_posix())
    return output_path


def audit_front_matter(path: str | Path) -> dict[str, Any]:
    """Perform structural checks that do not depend on a particular renderer."""
    source = Path(path)
    with ZipFile(source) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    body = root.find("./w:body", NS)
    if body is None:
        raise FrontMatterError("DOCX 缺少 document body")
    tables = _top_level_tables(body)
    visible = "".join(root.xpath(".//w:t/text()", namespaces=NS))
    problems: list[str] = []
    if len(tables) != 2:
        problems.append(f"顶层表格数 {len(tables)} != 2")
    # Build historical source markers from code points so the public source tree
    # itself does not republish the values it is meant to reject.
    forbidden_public_markers = (
        "".join(chr(value) for value in (0x56FD, 0x6052)),
        "".join(
            chr(value)
            for value in (
                0x6210, 0x90FD, 0x56FD, 0x6052, 0x7A7A, 0x95F4, 0x6280, 0x672F,
                0x5DE5, 0x7A0B, 0x80A1, 0x4EFD, 0x6709, 0x9650, 0x516C, 0x53F8,
            )
        ),
    )
    for marker in forbidden_public_markers:
        if marker in visible:
            problems.append(f"母版包含禁止公开的组织标识：{marker}")
    for stale in ("XXXXXX", "软件部署手册"):
        if stale in visible:
            problems.append(f"仍含母版占位文本：{stale}")
    required = ("档案编号：", "签 署 页", "变更履历", "编制：", "批准：")
    for marker in required:
        if marker not in visible:
            problems.append(f"缺少前三页标记：{marker}")
    return {
        "path": str(source),
        "ok": not problems,
        "top_level_tables": len(tables),
        "problems": problems,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="填充统一首页/签字页/变更履历母版")
    parser.add_argument("--template", required=True)
    parser.add_argument("--data", required=True, help="JSON/YAML 数据文件")
    parser.add_argument("--output", required=True)
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--audit-json")
    args = parser.parse_args(argv)

    payload = load_payload(args.data)
    result = render_front_matter(
        args.template, payload, args.output, release=args.release
    )
    audit = audit_front_matter(result)
    if args.audit_json:
        Path(args.audit_json).write_text(
            json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    if not audit["ok"]:
        raise FrontMatterError("；".join(audit["problems"]))
    print(result)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
