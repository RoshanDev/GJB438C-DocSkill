from __future__ import annotations

import base64
from dataclasses import dataclass
import gzip
from hashlib import sha256
from pathlib import Path
import re
from zipfile import ZipFile

from lxml import etree
import yaml

from .markdown_doc import split_front_matter
from .render import (
    BOOKMARK_NAME,
    DOCVAR_HASH,
    DOCVAR_PREFIX,
    _normalized_bookmark_text,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


class ImportWordError(RuntimeError):
    pass


@dataclass(slots=True)
class ImportResult:
    output: Path
    exact_round_trip: bool
    warning: str | None = None


def _doc_vars(settings_xml: bytes) -> dict[str, str]:
    root = etree.fromstring(settings_xml)
    result: dict[str, str] = {}
    for variable in root.xpath("./w:docVars/w:docVar", namespaces=NS):
        name = variable.get(f"{{{W}}}name")
        value = variable.get(f"{{{W}}}val", "")
        if name:
            result[name] = value
    return result


def _embedded_source(variables: dict[str, str]) -> str | None:
    chunks = [
        (name, value)
        for name, value in variables.items()
        if re.fullmatch(re.escape(DOCVAR_PREFIX) + r"\d{4}", name)
    ]
    if not chunks:
        return None
    encoded = "".join(value for name, value in sorted(chunks))
    try:
        return gzip.decompress(base64.b64decode(encoded)).decode("utf-8")
    except Exception as exc:
        raise ImportWordError(f"嵌入的 Markdown 基线损坏：{exc}") from exc


def _style_names(styles_xml: bytes) -> dict[str, str]:
    root = etree.fromstring(styles_xml)
    result: dict[str, str] = {}
    for style in root.xpath("./w:style", namespaces=NS):
        style_id = style.get(f"{{{W}}}styleId")
        name_node = style.find("./w:name", NS)
        if style_id and name_node is not None:
            result[style_id] = name_node.get(f"{{{W}}}val", style_id)
    return result


def _paragraph_text(element: etree._Element) -> str:
    return "".join(element.xpath(".//w:t/text()", namespaces=NS)).strip()


def _table_markdown(table: etree._Element) -> list[str]:
    rows: list[list[str]] = []
    for row in table.findall("./w:tr", NS):
        values = []
        for cell in row.findall("./w:tc", NS):
            value = " ".join(
                text.strip()
                for text in cell.xpath(".//w:t/text()", namespaces=NS)
                if text.strip()
            )
            values.append(value.replace("|", "\\|"))
        rows.append(values)
    if not rows:
        return []
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    lines = ["| " + " | ".join(normalized[0]) + " |"]
    lines.append("| " + " | ".join("---" for _ in range(width)) + " |")
    lines.extend("| " + " | ".join(row) + " |" for row in normalized[1:])
    return lines


def _candidate_body(document_xml: bytes, styles_xml: bytes) -> str:
    root = etree.fromstring(document_xml)
    body = root.find("./w:body", NS)
    if body is None:
        raise ImportWordError("DOCX 缺少 document body")
    names = _style_names(styles_xml)
    active = False
    body_id = None
    lines: list[str] = []
    for child in body:
        starts = child.xpath(
            './/w:bookmarkStart[@w:name=$name]', namespaces=NS, name=BOOKMARK_NAME
        )
        if starts:
            active = True
            body_id = starts[0].get(f"{{{W}}}id")
        if not active:
            continue
        local = etree.QName(child).localname
        if local == "p":
            text = _paragraph_text(child)
            pstyle = child.find("./w:pPr/w:pStyle", NS)
            style_name = names.get(pstyle.get(f"{{{W}}}val"), "") if pstyle is not None else ""
            heading = re.search(r"GJB 标题 ([1-9])", style_name)
            if heading and text:
                lines.extend(["#" * int(heading.group(1)) + " " + text, ""])
            elif text:
                lines.extend([text, ""])
            elif child.xpath(".//w:drawing|.//w:pict", namespaces=NS):
                lines.extend(["[图片或图形保留在 Word 中，回流后需人工核对]", ""])
        elif local == "tbl":
            lines.extend(_table_markdown(child))
            lines.append("")
        if child.xpath(".//w:bookmarkEnd[@w:id=$id]", namespaces=NS, id=body_id):
            break
    value = "\n".join(lines).strip()
    if not value:
        raise ImportWordError(f"未在书签 {BOOKMARK_NAME} 中提取到正文")
    return value + "\n"


def import_word(input_docx: str | Path, output_markdown: str | Path) -> ImportResult:
    source = Path(input_docx)
    output = Path(output_markdown)
    with ZipFile(source) as archive:
        document_xml = archive.read("word/document.xml")
        settings_xml = archive.read("word/settings.xml")
        styles_xml = archive.read("word/styles.xml")
    variables = _doc_vars(settings_xml)
    embedded = _embedded_source(variables)
    current_hash = sha256(_normalized_bookmark_text(document_xml).encode("utf-8")).hexdigest()
    stored_hash = variables.get(DOCVAR_HASH)

    exact = embedded is not None and stored_hash == current_hash
    warning = None
    if exact:
        value = embedded
    else:
        candidate = _candidate_body(document_xml, styles_xml)
        if embedded:
            metadata, _, _, errors = split_front_matter(embedded)
            if errors:
                metadata = {}
        else:
            metadata = {}
        metadata.pop("approval", None)
        metadata.setdefault("document", {})["status"] = "draft"
        metadata.setdefault("round_trip", {})
        metadata["round_trip"].update(
            {
                "source_docx": source.name,
                "exact": False,
                "requires_review": True,
            }
        )
        front = yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip()
        warning = (
            "Word 正文已变化，嵌入的 Markdown 基线不再与可见正文一致；"
            "已生成候选 Markdown，必须重新审核结构化证据块和追踪关系。"
        )
        value = f"---\n{front}\n---\n\n<!-- {warning} -->\n\n{candidate}"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(value, encoding="utf-8")
    return ImportResult(output, exact, warning)
