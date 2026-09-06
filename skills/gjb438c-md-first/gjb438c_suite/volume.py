from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

from pypdf import PdfReader
from zipfile import ZipFile
from lxml import etree
from .registry import get_document_type

from .markdown_doc import MarkdownDocument, parse_markdown, strip_quality_blocks
from .profile_quality import (
    ProfileQualityError,
    is_fixture,
    load_profile_mapping,
    normalize_tier,
    resolve_document_tier,
)


class VolumeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RenderedPageMetrics:
    total_pages: int
    body_start_page: int
    body_pages: int
    visible_characters: int
    thin_pages: int
    thin_page_ratio: float
    duplicate_pages: int
    duplicate_page_ratio: float
    minimum_page_characters: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VolumeResult:
    document_type: str
    tier: str
    total_pages: int
    body_start_page: int
    body_pages: int
    minimum_body_pages: int
    visible_characters: int
    minimum_visible_characters: int
    effective_units: int
    duplicate_prose_ratio: float
    duplicate_page_ratio: float
    thin_page_ratio: float
    passed: bool
    issues: tuple[str, ...]
    source_sha256: str
    docx_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        state = "PASS" if self.passed else "FAIL"
        lines = [
            f"[{state}] volume {self.document_type} tier={self.tier} "
            f"body_pages={self.body_pages}/{self.minimum_body_pages} "
            f"visible_chars={self.visible_characters}/{self.minimum_visible_characters} "
            f"thin={self.thin_page_ratio:.2%} duplicate_pages={self.duplicate_page_ratio:.2%} "
            f"duplicate_prose={self.duplicate_prose_ratio:.2%}"
        ]
        lines.extend(f"- {item}" for item in self.issues)
        return "\n".join(lines)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_tier(document: MarkdownDocument, explicit: str | None = None) -> str:
    return resolve_document_tier(document, explicit)


def _policy(document_type: str, tier: str) -> dict[str, Any]:
    mapping = load_profile_mapping(document_type)
    try:
        value = mapping["volume_policy"][normalize_tier(tier)]
    except KeyError as exc:
        raise VolumeError(f"缺少 {document_type}/{tier} 体量策略") from exc
    if not isinstance(value, dict):
        raise VolumeError(f"无效体量策略：{document_type}/{tier}")
    return value


def volume_policy(document_type: str, tier: str) -> dict[str, Any]:
    normalized = normalize_tier(tier)
    result = dict(_policy(document_type.upper(), normalized))
    result.update({"document_type": document_type.upper(), "tier": normalized})
    return result


def minimum_body_pages(
    document_type: str,
    tier: str,
    override: int | None = None,
) -> int:
    normalized = normalize_tier(tier)
    floor = int(_policy(document_type.upper(), normalized).get("minimum_pages", 0))
    if override is None:
        return floor
    if isinstance(override, bool) or not isinstance(override, int) or override <= 0:
        raise VolumeError('minimum page override must be a positive integer')
    requested = override
    if requested < floor:
        raise VolumeError(
            f"--min-body-pages 只能提高下限；{document_type.upper()}/{normalized} "
            f"策略下限为 {floor}，不能降为 {requested}"
        )
    return requested


def _visible_markdown_text(document: MarkdownDocument) -> str:
    body = strip_quality_blocks(document.body)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = re.sub(r"!\[[^]]*\]\([^)]*\)", "", body)
    body = re.sub(r"<[^>]+>", "", body)
    return body


def visible_markdown_characters(document: MarkdownDocument) -> int:
    return len(re.sub(r"\s+", "", _visible_markdown_text(document)))


def _normalized_prose_paragraphs(document: MarkdownDocument) -> list[str]:
    result: list[str] = []
    for block in re.split(r"\n\s*\n+", _visible_markdown_text(document)):
        lines: list[str] = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^\|(?:\s*:?-{3,}:?\s*\|)+\s*$", stripped):
                continue
            lines.append(stripped)
        normalized = re.sub(r"[\s\W_]+", "", "".join(lines), flags=re.UNICODE)
        if len(normalized) >= 40:
            result.append(normalized)
    return result


def duplicate_prose_metrics(document: MarkdownDocument) -> tuple[int, float, int]:
    paragraphs = _normalized_prose_paragraphs(document)
    if not paragraphs:
        return 0, 0.0, 0
    counts = Counter(paragraphs)
    total = sum(len(item) for item in paragraphs)
    duplicate = sum((count - 1) * len(item) for item, count in counts.items())
    return duplicate, (duplicate / total if total else 0.0), max(counts.values(), default=0)


def _table_count(document: MarkdownDocument) -> int:
    return sum(
        1
        for line in _visible_markdown_text(document).splitlines()
        if re.match(r"^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$", line)
    )


def _figure_count(document: MarkdownDocument) -> int:
    return len(re.findall(r"!\[[^]]*\]\([^)]*\)", strip_quality_blocks(document.body)))


def effective_units(document: MarkdownDocument) -> tuple[int, int]:
    visible = visible_markdown_characters(document)
    duplicate, _, _ = duplicate_prose_metrics(document)
    deduplicated = max(0, visible - duplicate)
    artifacts = len(tuple(getattr(document, "artifacts", ()) or ()))
    units = deduplicated + _table_count(document) * 350 + _figure_count(document) * 450 + artifacts * 120
    return visible, units


def _scaled_visible_floor(document_type: str, tier: str, body_pages: int) -> int:
    policy = _policy(document_type, tier)
    base_pages = max(1, int(policy.get("minimum_pages", 1)))
    base_chars = max(0, int(policy.get("minimum_visible_characters", 0)))
    return max(base_chars, math.ceil(base_chars / base_pages * body_pages))


def markdown_volume_issues(
    document: MarkdownDocument,
    document_type: str,
    tier: str,
    audit_profile: str,
    *,
    min_body_pages_override: int | None = None,
) -> list[dict[str, Any]]:
    normalized = resolve_tier(document, tier)
    policy = _policy(document_type, normalized)
    floor = _document_floor(document, document_type, normalized, min_body_pages_override)
    visible, units = effective_units(document)
    visible_floor = _scaled_visible_floor(document_type, normalized, floor)
    _, duplicate_ratio, max_repeat = duplicate_prose_metrics(document)
    duplicate_limit = float(policy.get("maximum_duplicate_page_ratio", 0.08))
    severity = "ERROR" if audit_profile in {"review", "release"} else "WARN"
    issues: list[dict[str, Any]] = []
    quality = document.metadata.get("quality")
    declared = isinstance(quality, dict) and (quality.get("tier") or quality.get("scale"))
    if audit_profile == "release" and not declared:
        issues.append(
            {"severity": "ERROR", "code": "VOLUME_TIER_REQUIRED", "message": "发布文档必须显式声明 quality.tier/scale"}
        )
    if audit_profile == "release" and normalized == "prototype" :
        issues.append(
            {
                "severity": "ERROR",
                "code": "VOLUME_PROTOTYPE_RELEASE_FORBIDDEN",
                "message": "prototype 仅供仓库示例/CI；生产发布必须选择 standard、large 或 critical",
            }
        )
    if visible < visible_floor:
        issues.append(
            {
                "severity": severity,
                "code": "VOLUME_VISIBLE_CONTENT_TOO_THIN",
                "message": f"可见正文字符 {visible} 低于 {document_type}/{normalized} 最低值 {visible_floor}",
            }
        )
    if max_repeat >= 3 and duplicate_ratio > duplicate_limit:
        issues.append(
            {
                "severity": severity,
                "code": "VOLUME_DUPLICATE_CONTENT",
                "message": f"重复长段落占比 {duplicate_ratio:.2%} 超过 {duplicate_limit:.2%}，最大重复次数 {max_repeat}",
            }
        )
    if units < visible_floor:
        issues.append(
            {
                "severity": severity,
                "code": "VOLUME_EFFECTIVE_CONTENT_TOO_THIN",
                "message": f"去重后的等效内容单位 {units} 低于 {visible_floor}",
            }
        )
    return issues


def _office() -> str:
    candidates = (
        shutil.which("libreoffice"),
        shutil.which("soffice"),
        shutil.which("soffice.exe"),
        r"C:\Program Files\LibreOffice\program\soffice.exe",
    )
    for value in candidates:
        if value and Path(value).exists():
            return str(value)
    raise VolumeError("release 页数门禁需要 LibreOffice/soffice，不能用 DOCX 元数据代替真实渲染")


def _normalized_page_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or re.fullmatch(r"[-—–]?\s*\d+\s*[-—–]?", stripped):
            continue
        lines.append(stripped)
    return re.sub(r"[\s\W_]+", "", "".join(lines), flags=re.UNICODE)


def _body_start(reader: PdfReader, docx: Path) -> int:
    """Use the exported outline destination of the bookmarked first heading.

    Never guess page four: a long TOC is not body content. Missing or ambiguous
    destinations fail closed rather than inflating the page count.
    """
    with ZipFile(docx) as archive:
        root = etree.fromstring(archive.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    starts = root.xpath('.//w:bookmarkStart[@w:name="GJB_BODY"]', namespaces=ns)
    if len(starts) != 1:
        raise VolumeError("需要唯一的 GJB_BODY 正文书签")
    paragraph = starts[0].getparent()
    title = "".join(paragraph.xpath('.//w:t/text()', namespaces=ns)).strip()
    if not title:
        raise VolumeError("正文起点不是可识别的标题")
    hits = []
    def visit(items):
        for item in items:
            if isinstance(item, list):
                visit(item)
            elif str(item.get('/Title', '')).strip() == title:
                hits.append(reader.get_destination_page_number(item))
    visit(reader.outline)
    if len(hits) != 1 or hits[0] is None or hits[0] < 4:
        raise VolumeError("无法唯一定位前三页及目录之后的正文起点")
    return hits[0]


def _binding(document: MarkdownDocument, docx: Path) -> None:
    from .import_word import _doc_vars, _embedded_source
    from .render import DOCVAR_HASH, _normalized_bookmark_text
    with ZipFile(docx) as archive:
        variables = _doc_vars(archive.read('word/settings.xml'))
        body = _normalized_bookmark_text(archive.read('word/document.xml'))
    if _embedded_source(variables) != document.raw:
        raise VolumeError('DOCX 嵌入基线与当前 Markdown 不一致')
    if variables.get(DOCVAR_HASH) != sha256_text(body):
        raise VolumeError('DOCX 可见正文已修改；请回流并重新审核')


def _document_floor(document, code, tier, override):
    quality = document.metadata.get('quality') or {}
    if not isinstance(quality, dict):
        raise VolumeError('quality 必须为映射')
    declared = quality.get('min_body_pages')
    values = [minimum_body_pages(code, tier, v) for v in (declared, override) if v is not None]
    return max([minimum_body_pages(code, tier), *values])


def rendered_page_metrics(
    docx: str | Path,
    *,
    body_start_page: int | None = None,
    minimum_page_characters: int = 100,
) -> RenderedPageMetrics:
    source = Path(docx).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    with tempfile.TemporaryDirectory(prefix="gjb438c-pages-") as name:
        out = Path(name)
        profile = out / "lo-profile"
        profile.mkdir()
        command = [
            _office(),
            f"-env:UserInstallation={profile.as_uri()}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out),
            str(source),
        ]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        pdf = out / f"{source.stem}.pdf"
        if result.returncode or not pdf.is_file():
            raise VolumeError("LibreOffice 页数渲染失败：" + (result.stderr.strip() or result.stdout.strip()))
        reader = PdfReader(str(pdf))
        page_texts = [(page.extract_text() or "") for page in reader.pages]
        detected_start = _body_start(reader, source) if body_start_page is None else None
    total = len(page_texts)
    if body_start_page is None:
        start_index = detected_start
    else:
        if body_start_page < 1 or body_start_page > max(1, total):
            raise VolumeError(f"body_start_page 超出范围：{body_start_page}/{total}")
        start_index = body_start_page - 1
    body = page_texts[start_index:]
    normalized = [_normalized_page_text(item) for item in body]
    visible = sum(len(item) for item in normalized)
    thin = sum(len(item) < minimum_page_characters for item in normalized)
    eligible = [item for item in normalized if len(item) >= minimum_page_characters]
    counts = Counter(eligible)
    duplicate = sum(count - 1 for count in counts.values())
    body_pages = len(body)
    return RenderedPageMetrics(
        total_pages=total,
        body_start_page=start_index + 1,
        body_pages=body_pages,
        visible_characters=visible,
        thin_pages=thin,
        thin_page_ratio=(thin / body_pages if body_pages else 1.0),
        duplicate_pages=duplicate,
        duplicate_page_ratio=(duplicate / body_pages if body_pages else 1.0),
        minimum_page_characters=minimum_page_characters,
    )


def audit_rendered_volume(
    source: str | Path | MarkdownDocument,
    document_type: str,
    docx: str | Path,
    *,
    tier: str | None = None,
    min_body_pages_override: int | None = None,
    body_start_page: int | None = None,
) -> VolumeResult:
    document = source if isinstance(source, MarkdownDocument) else parse_markdown(source)
    normalized = resolve_tier(document, tier)
    canonical = get_document_type(document_type).code
    if get_document_type(str((document.metadata.get('document') or {}).get('type', ''))).code != canonical:
        raise VolumeError('文档类型与体量策略类型不匹配')
    _binding(document, Path(docx))
    if body_start_page is not None:
        raise VolumeError('正式体量审计不接受手工正文起始页')
    policy = _policy(document_type, normalized)
    floor = _document_floor(document, document_type, normalized, min_body_pages_override)
    base_pages = max(1, int(policy.get("minimum_pages", 1)))
    base_chars = max(0, int(policy.get("minimum_visible_characters", 0)))
    per_page = max(80, min(240, math.floor(base_chars / base_pages * 0.35)))
    metrics = rendered_page_metrics(
        docx,
        body_start_page=body_start_page,
        minimum_page_characters=per_page,
    )
    visible_floor = _scaled_visible_floor(document_type, normalized, floor)
    _, effective = effective_units(document)
    _, duplicate_prose_ratio, _ = duplicate_prose_metrics(document)
    max_thin = float(policy.get("maximum_thin_page_ratio", 0.2))
    max_duplicate = float(policy.get("maximum_duplicate_page_ratio", 0.08))
    issues: list[str] = [i['message'] for i in markdown_volume_issues(
        document, document_type, normalized, 'release', min_body_pages_override=floor
    ) if i['severity'] == 'ERROR']
    if metrics.body_pages < floor:
        issues.append(f"正文页数 {metrics.body_pages} 低于 {document_type}/{normalized} 发布下限 {floor}")
    if metrics.visible_characters < visible_floor:
        issues.append(f"Word 可见正文字符 {metrics.visible_characters} 低于最低值 {visible_floor}")
    if metrics.thin_page_ratio > max_thin:
        issues.append(f"薄页比例 {metrics.thin_page_ratio:.2%} 超过 {max_thin:.2%}")
    if metrics.duplicate_page_ratio > max_duplicate:
        issues.append(f"重复页比例 {metrics.duplicate_page_ratio:.2%} 超过 {max_duplicate:.2%}")
    if duplicate_prose_ratio > max_duplicate:
        issues.append(f"Markdown 重复长段落比例 {duplicate_prose_ratio:.2%} 超过 {max_duplicate:.2%}")
    return VolumeResult(
        document_type=get_document_type(document_type).code,
        tier=normalized,
        total_pages=metrics.total_pages,
        body_start_page=metrics.body_start_page,
        body_pages=metrics.body_pages,
        minimum_body_pages=floor,
        visible_characters=metrics.visible_characters,
        minimum_visible_characters=visible_floor,
        effective_units=effective,
        duplicate_prose_ratio=round(duplicate_prose_ratio, 6),
        duplicate_page_ratio=round(metrics.duplicate_page_ratio, 6),
        thin_page_ratio=round(metrics.thin_page_ratio, 6),
        passed=not issues,
        issues=tuple(issues),
        source_sha256=sha256_text(document.raw),
        docx_sha256=sha256_file(docx),
    )
