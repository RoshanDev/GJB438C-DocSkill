from __future__ import annotations

from pathlib import Path
import re
import shutil
import textwrap
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/gjb438c-md-first"
PKG = SKILL / "gjb438c_suite"
DATA = PKG / "data"
PROFILES = DATA / "profiles"

assert PROFILES.is_dir(), PROFILES

for rel in (
    ".github/workflows/analyze-template-pages.yml",
    ".github/workflows/export-gjb438c-feature-source.yml",
):
    path = ROOT / rel
    if path.exists():
        path.unlink()
shutil.rmtree(ROOT / ".bootstrap-v03", ignore_errors=True)

policy = {
    "policy_version": 1,
    "status": "repository-engineering-policy",
    "statement": "Page floors are project-scale quality gates, not universal GJB 438C requirements. Page count never substitutes for evidence coverage.",
    "scales": ["prototype", "small", "medium", "large", "very-large"],
    "documents": {
        "SDP":  {"prototype": 1, "small": 20, "medium": 40, "large": 70, "very-large": 110},
        "SIP":  {"prototype": 1, "small": 10, "medium": 18, "large": 30, "very-large": 45},
        "STrP": {"prototype": 1, "small": 10, "medium": 18, "large": 30, "very-large": 45},
        "STP":  {"prototype": 1, "small": 25, "medium": 55, "large": 100, "very-large": 160},
        "OCD":  {"prototype": 1, "small": 18, "medium": 35, "large": 60, "very-large": 90},
        "SSS":  {"prototype": 1, "small": 50, "medium": 110, "large": 200, "very-large": 350},
        "IRS":  {"prototype": 1, "small": 35, "medium": 75, "large": 130, "very-large": 220},
        "SSDD": {"prototype": 1, "small": 70, "medium": 150, "large": 260, "very-large": 450},
        "IDD":  {"prototype": 1, "small": 40, "medium": 90, "large": 160, "very-large": 280},
        "SRS":  {"prototype": 1, "small": 60, "medium": 130, "large": 220, "very-large": 400},
        "SDD":  {"prototype": 1, "small": 80, "medium": 170, "large": 300, "very-large": 550},
        "DBDD": {"prototype": 1, "small": 40, "medium": 85, "large": 150, "very-large": 260},
        "STD":  {"prototype": 1, "small": 90, "medium": 220, "large": 450, "very-large": 900},
        "STR":  {"prototype": 1, "small": 55, "medium": 130, "large": 230, "very-large": 500},
        "SPS":  {"prototype": 1, "small": 25, "medium": 50, "large": 85, "very-large": 140},
        "SVD":  {"prototype": 1, "small": 8, "medium": 14, "large": 22, "very-large": 35},
        "SUM":  {"prototype": 1, "small": 50, "medium": 110, "large": 200, "very-large": 350},
        "CPM":  {"prototype": 1, "small": 35, "medium": 75, "large": 130, "very-large": 220},
        "FSM":  {"prototype": 1, "small": 25, "medium": 50, "large": 85, "very-large": 140},
        "SDSR": {"prototype": 1, "small": 18, "medium": 35, "large": 60, "very-large": 90},
    },
    "portfolio_min_pages": {
        "prototype": 20,
        "small": 750,
        "medium": 1700,
        "large": 3150,
        "very-large": 5765,
    },
    "text_equivalent_chars_per_page": 260,
    "minimum_heading_coverage_percent": {
        "prototype": 0,
        "small": 70,
        "medium": 80,
        "large": 90,
        "very-large": 95,
    },
    "repeatable_artifact_minima": {
        "requirement": {"prototype": 1, "small": 10, "medium": 40, "large": 100, "very-large": 220},
        "interface-requirement": {"prototype": 1, "small": 5, "medium": 15, "large": 35, "very-large": 70},
        "design-unit": {"prototype": 1, "small": 4, "medium": 12, "large": 30, "very-large": 70},
        "interface": {"prototype": 1, "small": 4, "medium": 12, "large": 30, "very-large": 70},
        "message": {"prototype": 1, "small": 4, "medium": 15, "large": 40, "very-large": 100},
        "data": {"prototype": 1, "small": 4, "medium": 12, "large": 30, "very-large": 70},
        "data-model": {"prototype": 1, "small": 1, "medium": 2, "large": 4, "very-large": 8},
        "table": {"prototype": 1, "small": 5, "medium": 20, "large": 50, "very-large": 120},
        "scenario": {"prototype": 1, "small": 4, "medium": 12, "large": 30, "very-large": 70},
        "test-case": {"prototype": 1, "small": 20, "medium": 100, "large": 300, "very-large": 800},
        "test-result": {"prototype": 1, "small": 20, "medium": 100, "large": 300, "very-large": 800},
        "task": {"prototype": 1, "small": 5, "medium": 20, "large": 50, "very-large": 120},
        "change": {"prototype": 1, "small": 3, "medium": 10, "large": 25, "very-large": 60},
        "product": {"prototype": 1, "small": 2, "medium": 5, "large": 12, "very-large": 30},
        "component": {"prototype": 1, "small": 4, "medium": 12, "large": 30, "very-large": 70},
        "firmware-item": {"prototype": 1, "small": 2, "medium": 6, "large": 15, "very-large": 35},
    },
}
DATA.mkdir(parents=True, exist_ok=True)
(DATA / "volume-policy.yaml").write_text(
    yaml.safe_dump(policy, allow_unicode=True, sort_keys=False), encoding="utf-8"
)

(PKG / "profiles.py").write_text(r'''from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .markdown_doc import Heading
from .registry import DocumentType, get_document_type

PROFILE_ROOT = Path(__file__).resolve().parent / "data" / "profiles"


@dataclass(frozen=True, slots=True)
class DocumentProfile:
    document_type: DocumentType
    path: Path
    raw: dict[str, Any]
    outline: tuple[Heading, ...]
    artifact_contracts: dict[str, dict[str, Any]]


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for nested in value.values():
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)


def _lists(raw: dict[str, Any]) -> Iterable[list[Any]]:
    keys = ("outline", "headings", "sections", "chapters")
    for key in keys:
        if isinstance(raw.get(key), list):
            yield raw[key]
    for mapping in _walk(raw):
        for key in keys:
            if isinstance(mapping.get(key), list):
                yield mapping[key]


def _outline(raw: dict[str, Any], path: Path) -> tuple[Heading, ...]:
    for candidate in _lists(raw):
        result: list[Heading] = []
        for entry in candidate:
            if isinstance(entry, str):
                result.append(Heading(1, entry.strip(), 0, None))
                continue
            if not isinstance(entry, dict):
                result = []
                break
            title = str(entry.get("title") or entry.get("name") or entry.get("heading") or "").strip()
            if not title:
                result = []
                break
            number = entry.get("number") or entry.get("id") or entry.get("clause")
            level = entry.get("level") or entry.get("depth")
            if level is None and number:
                value = str(number)
                level = value.count(".") + 1 if value[:1].isdigit() else 1
            try:
                level = max(1, min(9, int(level or 1)))
            except (TypeError, ValueError):
                level = 1
            result.append(Heading(level, title, 0, str(number).strip() if number else None))
        if len(result) >= 3:
            return tuple(result)
    raise ValueError(f"自包含 Profile 缺少有效章节目录：{path}")


def _fields(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return _fields(value.get("required") or value.get("required_fields"))
    return ()


def _contracts(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    containers: list[Any] = []
    for mapping in _walk(raw):
        for key in ("artifact_contracts", "evidence_contracts", "contracts", "artifacts"):
            if key in mapping:
                containers.append(mapping[key])
    result: dict[str, dict[str, Any]] = {}
    for container in containers:
        if isinstance(container, dict):
            entries = []
            for kind, spec in container.items():
                if isinstance(spec, dict):
                    entries.append({"kind": kind, **spec})
                elif isinstance(spec, list):
                    entries.append({"kind": kind, "required_fields": spec})
            container = entries
        if not isinstance(container, list):
            continue
        for entry in container:
            if not isinstance(entry, dict):
                continue
            kind = str(entry.get("kind") or entry.get("type") or entry.get("name") or "")
            kind = kind.strip().lower().replace("_", "-")
            if not kind:
                continue
            fields = _fields(entry.get("required_fields") or entry.get("required") or entry.get("fields"))
            try:
                minimum = max(1, int(entry.get("min_count", entry.get("minimum", 1))))
            except (TypeError, ValueError):
                minimum = 1
            current = result.setdefault(kind, {"required_fields": (), "min_count": minimum})
            if fields:
                current["required_fields"] = fields
            current["min_count"] = max(int(current.get("min_count", 1)), minimum)
    return result


def profile_path(value: str | DocumentType) -> Path:
    item = get_document_type(value) if isinstance(value, str) else value
    return PROFILE_ROOT / f"{item.code.lower()}.yaml"


def load_profile(value: str | DocumentType) -> DocumentProfile:
    item = get_document_type(value) if isinstance(value, str) else value
    path = profile_path(item)
    if not path.is_file():
        raise FileNotFoundError(f"未找到 {item.code} 自包含 Profile：{path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Profile 必须是 YAML 映射：{path}")
    contracts = _contracts(loaded)
    for kind in item.required_artifacts:
        contracts.setdefault(kind, {"required_fields": (), "min_count": 1})
    return DocumentProfile(item, path, loaded, _outline(loaded, path), contracts)


def iter_profiles() -> Iterable[DocumentProfile]:
    from .registry import iter_document_types
    for item in iter_document_types():
        yield load_profile(item)
''', encoding="utf-8")

(PKG / "volume.py").write_text(r'''from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any

import yaml
from pypdf import PdfReader

from .markdown_doc import MarkdownDocument, strip_quality_blocks
from .profiles import DocumentProfile

POLICY_PATH = Path(__file__).resolve().parent / "data" / "volume-policy.yaml"
VALID_SCALES = ("prototype", "small", "medium", "large", "very-large")


class VolumeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class VolumeResult:
    document_type: str
    scale: str
    pages: int
    minimum_pages: int
    visible_chars: int
    effective_units: int
    minimum_effective_units: int
    passed: bool
    issues: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "scale": self.scale,
            "pages": self.pages,
            "minimum_pages": self.minimum_pages,
            "visible_chars": self.visible_chars,
            "effective_units": self.effective_units,
            "minimum_effective_units": self.minimum_effective_units,
            "passed": self.passed,
            "issues": list(self.issues),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        state = "PASS" if self.passed else "FAIL"
        tail = "\n- " + "\n- ".join(self.issues) if self.issues else ""
        return (f"[{state}] volume {self.document_type} scale={self.scale} "
                f"pages={self.pages}/{self.minimum_pages} "
                f"effective_units={self.effective_units}/{self.minimum_effective_units}{tail}")


def load_volume_policy() -> dict[str, Any]:
    value = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise VolumeError(f"无效体量策略：{POLICY_PATH}")
    return value


def resolve_scale(document: MarkdownDocument, explicit: str | None = None) -> str:
    value = explicit
    if not value:
        quality = document.metadata.get("quality")
        project = document.metadata.get("project")
        if isinstance(quality, dict):
            value = quality.get("scale")
        if not value and isinstance(project, dict):
            value = project.get("scale")
    normalized = str(value or "prototype").strip().lower().replace("_", "-")
    if normalized not in VALID_SCALES:
        raise VolumeError(f"scale 必须是 {', '.join(VALID_SCALES)}，实际为 {normalized!r}")
    return normalized


def has_declared_scale(document: MarkdownDocument, explicit: str | None = None) -> bool:
    if explicit:
        return True
    for key in ("quality", "project"):
        value = document.metadata.get(key)
        if isinstance(value, dict) and value.get("scale"):
            return True
    return False


def minimum_pages(document_type: str, scale: str, override: int | None = None) -> int:
    if override is not None:
        return max(0, int(override))
    try:
        return int(load_volume_policy()["documents"][document_type.upper()][scale])
    except KeyError as exc:
        raise VolumeError(f"缺少 {document_type}/{scale} 页数策略") from exc


def _visible_chars(document: MarkdownDocument) -> int:
    body = strip_quality_blocks(document.body)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = re.sub(r"!\[[^]]*\]\([^)]*\)", "", body)
    return len(re.sub(r"\s+", "", body))


def _table_count(document: MarkdownDocument) -> int:
    lines = strip_quality_blocks(document.body).splitlines()
    return sum(1 for line in lines if re.match(r"^\s*\|(?:\s*:?-{3,}:?\s*\|)+\s*$", line))


def _figure_count(document: MarkdownDocument) -> int:
    return len(re.findall(r"!\[[^]]*\]\([^)]*\)", strip_quality_blocks(document.body)))


def effective_units(document: MarkdownDocument) -> tuple[int, int]:
    chars = _visible_chars(document)
    return chars, chars + _table_count(document) * 700 + _figure_count(document) * 550 + len(document.artifacts) * 180


def markdown_volume_issues(document: MarkdownDocument, profile: DocumentProfile, scale: str,
                           audit_profile: str, scale_declared: bool) -> list[dict[str, Any]]:
    policy = load_volume_policy()
    severity = "ERROR" if audit_profile == "release" else "WARN"
    issues: list[dict[str, Any]] = []
    if audit_profile == "release" and not scale_declared:
        issues.append({"severity": "ERROR", "code": "VOLUME_SCALE_REQUIRED",
                       "message": "发布文档必须在 quality.scale/project.scale 或 --scale 中声明项目规模"})
    pages = minimum_pages(profile.document_type.code, scale)
    _, units = effective_units(document)
    floor = pages * int(policy.get("text_equivalent_chars_per_page", 260))
    if units < floor:
        issues.append({"severity": severity, "code": "VOLUME_EVIDENCE_TOO_THIN",
                       "message": f"{profile.document_type.code}/{scale} 等效内容单位 {units} 低于 {floor}；页数不能用空白或重复内容替代"})
    expected = {h.title.strip() for h in profile.outline if h.title.strip()}
    actual = {h.title.strip() for h in document.headings if h.title.strip()}
    coverage = len(expected & actual) / len(expected) * 100 if expected else 100
    required_coverage = float(policy["minimum_heading_coverage_percent"][scale])
    if coverage + 1e-9 < required_coverage:
        issues.append({"severity": severity, "code": "VOLUME_OUTLINE_COVERAGE_LOW",
                       "message": f"Profile 章节覆盖率 {coverage:.2f}% 低于 {required_coverage:.2f}%"})
    counts = Counter(a.kind for a in document.artifacts)
    repeatable = policy.get("repeatable_artifact_minima", {})
    for kind in profile.artifact_contracts:
        if kind in repeatable:
            required = int(repeatable[kind][scale])
            if counts[kind] < required:
                issues.append({"severity": severity, "code": "VOLUME_ARTIFACT_COUNT_LOW",
                               "message": f"gjb-{kind} 数量 {counts[kind]} 低于 {profile.document_type.code}/{scale} 最低值 {required}"})
    return issues


def _office() -> str:
    candidates = (shutil.which("libreoffice"), shutil.which("soffice"), shutil.which("soffice.exe"),
                  r"C:\Program Files\LibreOffice\program\soffice.exe")
    for value in candidates:
        if value and Path(value).exists():
            return str(value)
    raise VolumeError("页数门禁需要 LibreOffice/soffice；release 不允许跳过真实渲染页数")


def rendered_page_count(docx: str | Path) -> int:
    source = Path(docx).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    with tempfile.TemporaryDirectory(prefix="gjb438c-pages-") as name:
        out = Path(name)
        result = subprocess.run([_office(), "--headless", "--convert-to", "pdf", "--outdir", str(out), str(source)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
        pdf = out / f"{source.stem}.pdf"
        if result.returncode or not pdf.is_file():
            raise VolumeError("LibreOffice 页数渲染失败：" + (result.stderr.strip() or result.stdout.strip()))
        return len(PdfReader(str(pdf)).pages)


def audit_rendered_volume(document: MarkdownDocument, profile: DocumentProfile, docx: str | Path,
                          *, scale: str, min_pages_override: int | None = None) -> VolumeResult:
    pages = rendered_page_count(docx)
    floor = minimum_pages(profile.document_type.code, scale, min_pages_override)
    chars, units = effective_units(document)
    unit_floor = floor * int(load_volume_policy().get("text_equivalent_chars_per_page", 260))
    issues: list[str] = []
    if pages < floor:
        issues.append(f"渲染页数 {pages} 低于 {profile.document_type.code}/{scale} 发布下限 {floor}")
    if units < unit_floor:
        issues.append(f"等效内容单位 {units} 低于反灌水下限 {unit_floor}")
    return VolumeResult(profile.document_type.code, scale, pages, floor, chars, units, unit_floor, not issues, tuple(issues))
''', encoding="utf-8")

(PKG / "profile_quality.py").write_text(r'''from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .markdown_doc import MarkdownDocument, parse_markdown
from .profiles import DocumentProfile, load_profile
from .quality import AuditReport, Issue, PROFILE_LEVEL, audit_markdown
from .registry import get_document_type
from .volume import has_declared_scale, markdown_volume_issues, resolve_scale


def _nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _add(report: AuditReport, severity: str, code: str, message: str, *, line=None, artifact_id=None) -> None:
    report.issues.append(Issue(severity, code, message, line, artifact_id))


def apply_profile_contracts(report: AuditReport, document: MarkdownDocument, profile: DocumentProfile) -> None:
    counts = Counter(a.kind for a in document.artifacts)
    for kind, contract in profile.artifact_contracts.items():
        minimum = int(contract.get("min_count", 1))
        if counts[kind] < minimum:
            _add(report, "ERROR" if report.profile == "release" else "WARN", "PROFILE_ARTIFACT_COUNT",
                 f"{profile.document_type.code} Profile 要求至少 {minimum} 个 gjb-{kind}，实际 {counts[kind]}")
        fields = tuple(contract.get("required_fields") or ())
        for artifact in document.artifacts_of(kind):
            for field in fields:
                if not _nonempty(artifact.data.get(field)):
                    _add(report, "ERROR" if PROFILE_LEVEL[report.profile] >= 1 else "WARN", "PROFILE_FIELD_MISSING",
                         f"gjb-{kind} 缺少 Profile 字段 {field}", line=artifact.line, artifact_id=artifact.identifier)
    expected = {h.title.strip() for h in profile.outline if h.title.strip()}
    actual = {h.title.strip() for h in document.headings if h.title.strip()}
    report.metrics["profile_heading_coverage_percent"] = round(len(expected & actual) / len(expected) * 100, 2) if expected else 100
    report.metrics["profile_contract_kinds"] = len(profile.artifact_contracts)


def audit_markdown_with_profile(path: str | Path, *, profile_name: str = "review",
                                document_type: str | None = None, baseline_srs: str | Path | None = None,
                                scale: str | None = None) -> AuditReport:
    report = audit_markdown(path, profile=profile_name, document_type=document_type, baseline_srs=baseline_srs)
    document = parse_markdown(path)
    declared = document_type or str(document.metadata.get("document", {}).get("type", ""))
    if not declared:
        return report
    try:
        doc_profile = load_profile(get_document_type(declared))
    except (ValueError, FileNotFoundError) as exc:
        _add(report, "ERROR", "PROFILE_LOAD_FAILED", str(exc))
        return report
    apply_profile_contracts(report, document, doc_profile)
    selected = resolve_scale(document, scale)
    for issue in markdown_volume_issues(document, doc_profile, selected, report.profile,
                                        has_declared_scale(document, scale)):
        _add(report, **issue)
    report.metrics["scale"] = selected
    return report
''', encoding="utf-8")

pyproject = SKILL / "pyproject.toml"
text = pyproject.read_text(encoding="utf-8")
if '"pypdf>=' not in text:
    text = text.replace('  "Pillow>=10.0"\n]', '  "Pillow>=10.0",\n  "pypdf>=5.0"\n]')
if "[tool.setuptools.package-data]" not in text:
    text += '\n[tool.setuptools.package-data]\ngjb438c_suite = ["data/*.yaml", "data/profiles/*.yaml"]\n'
pyproject.write_text(text, encoding="utf-8")

cli = PKG / "cli.py"
text = cli.read_text(encoding="utf-8")
text = text.replace('from .markdown_doc import extract_template_outline, render_skeleton\n',
                    'from .markdown_doc import extract_template_outline, parse_markdown, render_skeleton\n')
text = text.replace('from .quality import audit_markdown\n',
                    'from .quality import audit_markdown\nfrom .profile_quality import audit_markdown_with_profile\nfrom .profiles import load_profile\nfrom .volume import VolumeError, audit_rendered_volume, load_volume_policy, resolve_scale\n')
text = text.replace('    init.add_argument("--output", required=True)\n',
                    '    init.add_argument("--output", required=True)\n    init.add_argument("--source-template", action="store_true", help="显式从 --template-root 的 DOCX 重抽章节；默认使用安装包内置 Profile")\n')
text = text.replace('    audit.add_argument("--json")\n',
                    '    audit.add_argument("--json")\n    audit.add_argument("--scale", choices=["prototype", "small", "medium", "large", "very-large"])\n')
text = text.replace('    render.add_argument("--docx-audit-json")\n',
                    '    render.add_argument("--docx-audit-json")\n    render.add_argument("--scale", choices=["prototype", "small", "medium", "large", "very-large"])\n    render.add_argument("--min-pages", type=int, help="显式覆盖仓库工程页数下限；不是 GJB 条款")\n    render.add_argument("--volume-json")\n')
front_marker = '    front = sub.add_parser("front-matter", help="单独填充统一前三页")\n'
if 'volume-policy' not in text:
    text = text.replace(front_marker,
        '    policy = sub.add_parser("volume-policy", help="查看某文档类型/规模的工程体量门禁（非标准条款）")\n    policy.add_argument("--type", required=True)\n    policy.add_argument("--scale", choices=["prototype", "small", "medium", "large", "very-large"], required=True)\n\n' + front_marker)
old = '''        if args.command == "init":
            template = resolve_template(args.type, Path(args.template_root) if args.template_root else None)
            item = get_document_type(args.type)
            outline = extract_template_outline(template)
            project = _load_mapping(args.project)
'''
new = '''        if args.command == "init":
            item = get_document_type(args.type)
            if args.source_template or args.template_root:
                template = resolve_template(args.type, Path(args.template_root) if args.template_root else None)
                outline = extract_template_outline(template)
            else:
                outline = list(load_profile(item).outline)
            project = _load_mapping(args.project)
'''
assert old in text
text = text.replace(old, new)
old = '''            report = audit_markdown(
                args.input,
                profile=args.profile,
                document_type=args.type,
                baseline_srs=args.baseline_srs,
            )
'''
new = '''            report = audit_markdown_with_profile(
                args.input,
                profile_name=args.profile,
                document_type=args.type,
                baseline_srs=args.baseline_srs,
                scale=args.scale,
            )
'''
assert old in text
text = text.replace(old, new)
old = '''        if args.command == "render":
            result = render_document(
                args.input,
                args.output,
                profile=args.profile,
                baseline_srs=args.baseline_srs,
                front_template=args.front_template,
            )
'''
new = '''        if args.command == "render":
            source_doc = parse_markdown(args.input)
            selected_scale = resolve_scale(source_doc, args.scale)
            preflight = audit_markdown_with_profile(
                args.input,
                profile_name=args.profile,
                baseline_srs=args.baseline_srs,
                scale=args.scale,
            )
            if not preflight.passed:
                _write_report(preflight, None)
                return 2
            result = render_document(
                args.input,
                args.output,
                profile=args.profile,
                baseline_srs=args.baseline_srs,
                front_template=args.front_template,
            )
'''
assert old in text
text = text.replace(old, new)
needle = '''            print(result.output)
            print(report.to_text())
            return 0 if report.passed else 3

        if args.command == "refresh-toc":
'''
replacement = '''            declared_type = str(source_doc.metadata.get("document", {}).get("type", ""))
            volume = audit_rendered_volume(source_doc, load_profile(declared_type), result.output,
                                           scale=selected_scale, min_pages_override=args.min_pages)
            if args.volume_json:
                Path(args.volume_json).write_text(volume.to_json(), encoding="utf-8")
            print(result.output)
            print(report.to_text())
            print(volume.to_text())
            return 0 if report.passed and volume.passed else 3

        if args.command == "refresh-toc":
'''
assert needle in text
text = text.replace(needle, replacement)
needle = '        if args.command == "front-matter":\n'
if 'args.command == "volume-policy"' not in text:
    text = text.replace(needle, '''        if args.command == "volume-policy":
            item = get_document_type(args.type)
            policy = load_volume_policy()
            payload = {
                "status": policy.get("status"),
                "statement": policy.get("statement"),
                "document_type": item.code,
                "document_name": item.chinese_name,
                "scale": args.scale,
                "minimum_pages": policy["documents"][item.code][args.scale],
                "portfolio_min_pages": policy["portfolio_min_pages"][args.scale],
                "repeatable_artifact_minima": {
                    kind: values[args.scale]
                    for kind, values in policy.get("repeatable_artifact_minima", {}).items()
                    if kind in item.required_artifacts
                },
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0

        if args.command == "front-matter":
''')
text = text.replace('except (ValueError, FileNotFoundError, FrontMatterError, RenderError, ImportWordError, FinalizeError) as exc:',
                    'except (ValueError, FileNotFoundError, FrontMatterError, RenderError, ImportWordError, FinalizeError, VolumeError) as exc:')
cli.write_text(text, encoding="utf-8")

for name in ("SRS.example.md", "SDD.example.md"):
    path = SKILL / "examples" / name
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", raw, re.S)
    assert match
    metadata = yaml.safe_load(match.group(1)) or {}
    metadata["quality"] = {"scale": "prototype"}
    path.write_text("---\n" + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n" + raw[match.end():], encoding="utf-8")

for legacy in ("word-fillter-438c-srs", "word-fillter-438c-sdd"):
    source = ROOT / "skills" / legacy / "SKILL.md"
    target = ROOT / "skills" / legacy / "LEGACY.md"
    if source.exists():
        body = source.read_text(encoding="utf-8")
        body = re.sub(r"\A---.*?---\s*", "", body, flags=re.S)
        target.write_text("# 兼容旁路\n\n此目录仅在用户明确要求跳过 Markdown、直接填写既有 DOCX 模板时手工使用；它不再作为可自动发现的 Agent Skill。普通 SRS/SDD 请求使用 `gjb438c-srs`、`gjb438c-sdd` 或 `gjb438c-md-first`。\n\n" + body, encoding="utf-8")
        source.unlink()

(ROOT / "README.md").write_text('''# GJB438C-DocSkill

面向 GJB 438C-2021 二十类软件生命周期文档的 Markdown-first 编写、审查、DOCX 生成与回流工具集。

## 架构

仓库采用“一个共享核心 + 二十个文档 Profile + 二十个薄入口 Skill”。Markdown 是评审基线，Word 是发布物，并不复制为四十套实现。旧 SRS/SDD Word 锚点填充器保留为手工兼容旁路，但已移除 `SKILL.md`，不会再与主线抢触发。

安装 `skills/gjb438c-md-first` 后，`gjb438c init --type <TYPE>` 默认读取随包发布的 Profile，不依赖仓库根目录模板。`--template-root` 仅供维护者重新抽取和校准。

## 二十类文档

`SDP / SIP / STrP / STP / OCD / SSS / IRS / SSDD / IDD / SRS / SDD / DBDD / STD / STR / SPS / SVD / SUM / CPM / FSM / SDSR`

每类都有独立 Profile 和薄入口，例如 `gjb438c-srs`、`gjb438c-sdd`、`gjb438c-std`。共享引擎负责内容合同、来源证据、跨文档追踪、统一前三页、Markdown→DOCX、目录刷新、DOCX 审计和 Word 回流。

## 体量门禁

发布文档必须声明项目规模：`prototype / small / medium / large / very-large`。页数阈值是本仓库的反糊弄工程策略，不是 GJB 438C 的统一页数条款。

大型项目的 SRS、SSS、SDD、SSDD、STD、STR 等核心文档按数百页校验；SVD、SIP、STrP 等职责较窄的文档不强行灌水到数百页。页数门禁同时检查章节覆盖、可见正文、结构化证据以及需求、设计单元、接口、数据项和测试用例数量。空白页、重复段落和放大图片不能通过。

```bash
python -m pip install -e 'skills/gjb438c-md-first[test]'

gjb438c init --type SDD --project project.yaml --output docs/SDD.md
gjb438c audit docs/SDD.md --profile release --scale large --baseline-srs docs/SRS.md
gjb438c render docs/SDD.md --output dist/SDD.docx --profile release \
  --scale large --baseline-srs docs/SRS.md --refresh-toc \
  --volume-json dist/SDD.volume.json

gjb438c volume-policy --type SDD --scale large
```

格式、追踪和回流说明见 `skills/gjb438c-md-first/docs/`；页数策略见 `docs/VOLUME-POLICY.md`。

## 公开仓库安全

示例、测试和模板不得包含真实单位名称、项目代号、人员、IP 地址或内部拓扑。真实项目数据仅在用户本地填写。
''', encoding="utf-8")

skill_readme = SKILL / "README.md"
skill_readme.write_text('''# gjb438c-md-first

覆盖 GJB 438C-2021 二十类文档的自包含 Markdown-first 工具。

## 安装与初始化

```bash
python -m pip install -e '.[test]'
gjb438c list
gjb438c init --type SRS --project examples/project.yaml --output docs/SRS.md
```

二十个 Profile 位于 `gjb438c_suite/data/profiles/*.yaml`，会随包安装；普通使用不需要仓库根模板目录。

## 审核与发布

```bash
gjb438c audit docs/SRS.md --profile release --scale large
gjb438c audit docs/SDD.md --profile release --scale large --baseline-srs docs/SRS.md
gjb438c render docs/SDD.md --output dist/SDD.docx --profile release \
  --scale large --baseline-srs docs/SRS.md --refresh-toc \
  --volume-json dist/SDD.volume.json
gjb438c audit-docx dist/SDD.docx --profile release
gjb438c import-word dist/SDD-reviewed.docx --output docs/SDD-returned.md
```

`quality.scale` 或 `--scale` 决定工程体量门禁。大型项目的核心规格、设计和测试文档按数百页配置；短文档按职责设置较低门槛。页数之外还检查章节、正文等效内容、来源和结构化证据，禁止注水。
''', encoding="utf-8")

skill_md = SKILL / "SKILL.md"
raw = skill_md.read_text(encoding="utf-8")
if "## 体量不得靠页数注水" not in raw:
    raw += '''

## 体量不得靠页数注水

- 发布文档必须声明 `quality.scale`，或显式传入 `--scale`。
- `large` / `very-large` 的核心 SRS、SSS、SDD、SSDD、STD、STR 按数百页工程下限检查。
- 页数不是唯一判据；还必须满足章节覆盖、来源证据、需求/设计单元/接口/数据/测试用例数量及等效内容单位。
- 来源材料不足以支撑目标规模时必须阻断 release，并列出缺失证据；不得通过重复文字、空白页、放大图片或虚构项目事实凑页数。
'''
skill_md.write_text(raw, encoding="utf-8")

(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs/VOLUME-POLICY.md").write_text('''# 文档体量与页数门禁

GJB 438C-2021 的文档内容要求不能简化成“所有文件同一页数”。本仓库另设可配置工程门禁，防止几页式空壳交付，但不把这些阈值冒充为标准条文。

大型项目中，SRS、SSS、SDD、SSDD、STD、STR 等核心规格、设计和测试文档可以达到数百页；SIP、STrP、SVD 等职责较窄的文档不应为了外观统一强行扩充到数百页。

发布判定同时包含：

1. 项目规模 `prototype / small / medium / large / very-large`；
2. Profile 章节覆盖；
3. 来源、需求、设计、接口、数据、测试用例和追踪证据；
4. Markdown 等效内容单位；
5. LibreOffice 真实渲染后的 DOCX 页数。

页数满足但内容密度或证据数量不足仍然失败。具体阈值位于 `skills/gjb438c-md-first/gjb438c_suite/data/volume-policy.yaml`，组织级裁剪必须纳入配置管理和评审记录。
''', encoding="utf-8")

tests = SKILL / "tests"
(tests / "test_profiles_self_contained.py").write_text('''from pathlib import Path
import yaml
from gjb438c_suite.cli import main
from gjb438c_suite.profiles import iter_profiles
from gjb438c_suite.registry import iter_document_types


def test_all_twenty_profiles_are_self_contained():
    profiles = list(iter_profiles())
    assert len(profiles) == 20
    assert {p.document_type.code for p in profiles} == {d.code for d in iter_document_types()}
    for profile in profiles:
        assert profile.path.is_file()
        assert len(profile.outline) >= 3
        assert set(profile.document_type.required_artifacts) <= set(profile.artifact_contracts)


def test_init_uses_bundled_profiles_without_template_root(tmp_path: Path):
    project = tmp_path / "project.yaml"
    project.write_text(yaml.safe_dump({"project": {"name": "示例系统", "scale": "prototype"},
        "software": {"name": "示例软件", "version": "0.1", "identifier": "DEMO"},
        "organization": "编制单位", "classification": "公开", "date": "2026-01-01"}, allow_unicode=True), encoding="utf-8")
    for item in iter_document_types():
        output = tmp_path / f"{item.code}.md"
        assert main(["init", "--type", item.code, "--project", str(project), "--output", str(output)]) == 0
        assert output.is_file()
''', encoding="utf-8")

(tests / "test_volume_policy.py").write_text('''from gjb438c_suite.profiles import iter_profiles
from gjb438c_suite.volume import VALID_SCALES, load_volume_policy, minimum_pages


def test_every_document_has_every_scale():
    policy = load_volume_policy()
    assert policy["status"] == "repository-engineering-policy"
    for profile in iter_profiles():
        values = policy["documents"][profile.document_type.code]
        assert set(values) == set(VALID_SCALES)
        ordered = [values[name] for name in VALID_SCALES]
        assert ordered == sorted(ordered)


def test_large_core_documents_have_hundreds_page_floor():
    for code in ("SSS", "SRS", "SSDD", "SDD", "STD", "STR"):
        assert minimum_pages(code, "large") >= 200


def test_short_documents_are_not_padded_to_hundreds():
    for code in ("SIP", "STrP", "SVD"):
        assert minimum_pages(code, "large") < 100
''', encoding="utf-8")

(tests / "test_skill_routing.py").write_text('''from pathlib import Path
from gjb438c_suite.registry import iter_document_types


def test_twenty_thin_skills_exist():
    root = Path(__file__).resolve().parents[3]
    expected = {f"gjb438c-{item.code.lower()}" for item in iter_document_types()}
    actual = {p.name for p in (root / "skills").glob("gjb438c-*") if p.is_dir() and p.name != "gjb438c-md-first"}
    assert expected <= actual
    for name in expected:
        assert "gjb438c-md-first" in (root / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


def test_legacy_fillers_are_not_agent_skills():
    root = Path(__file__).resolve().parents[3]
    for name in ("word-fillter-438c-srs", "word-fillter-438c-sdd"):
        directory = root / "skills" / name
        assert not (directory / "SKILL.md").exists()
        assert "兼容旁路" in (directory / "LEGACY.md").read_text(encoding="utf-8")
''', encoding="utf-8")

workflow = ROOT / ".github/workflows/gjb438c-md-first.yml"
raw = workflow.read_text(encoding="utf-8")
raw = raw.replace("libreoffice-writer python3-uno poppler-utils", "libreoffice-writer python3-uno poppler-utils")
if "Self-contained profile smoke" not in raw:
    raw = raw.replace("      - name: Content gates\n", '''      - name: Self-contained profile smoke
        run: |
          for type in SDP SIP STrP STP OCD SSS IRS SSDD IDD SRS SDD DBDD STD STR SPS SVD SUM CPM FSM SDSR; do
            gjb438c init --type "$type" --project skills/gjb438c-md-first/examples/project.yaml --output "/tmp/$type.md"
          done
          gjb438c volume-policy --type SDD --scale large
      - name: Content gates
''')
workflow.write_text(raw, encoding="utf-8")

bootstrap = ROOT / ".github/workflows/apply-v03-profiles.yml"
self_path = Path(__file__)
bootstrap.unlink(missing_ok=True)
self_path.unlink(missing_ok=True)
print("v0.3 profile and volume integration applied")
