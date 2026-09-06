from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from .audit_docx import audit_docx
from .markdown_doc import MarkdownDocument, parse_markdown, render_skeleton
from .profile_quality import (
    VALID_TIERS,
    ProfileQualityError,
    artifact_kind,
    artifact_mapping,
    audit_markdown_with_profile,
    document_type_from_metadata,
    load_profile_mapping,
    normalize_tier,
)
from .profiles import load_profile, heading_outline
from .registry import get_document_type, iter_document_types
from .volume import (
    VolumeError,
    audit_rendered_volume,
    minimum_body_pages,
    sha256_file,
    sha256_text,
)


class SuiteError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SuiteIssue:
    severity: str
    code: str
    message: str
    document_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SuiteDocumentResult:
    document_type: str
    markdown: str
    docx: str
    volume_report: str
    body_pages: int = 0
    minimum_body_pages: int = 0
    passed: bool = False

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SuiteAuditReport:
    manifest: Path
    tier: str
    issues: list[SuiteIssue] = field(default_factory=list)
    documents: list[SuiteDocumentResult] = field(default_factory=list)
    total_body_pages: int = 0
    minimum_total_body_pages: int = 0

    @property
    def errors(self) -> list[SuiteIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def passed(self) -> bool:
        return not self.errors and bool(self.documents) and all(item.passed for item in self.documents)

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest": str(self.manifest),
            "tier": self.tier,
            "passed": self.passed,
            "summary": {
                "errors": len(self.errors),
                "warnings": sum(1 for item in self.issues if item.severity == "WARN"),
                "documents": len(self.documents),
                "total_body_pages": self.total_body_pages,
                "minimum_total_body_pages": self.minimum_total_body_pages,
            },
            "documents": [item.as_dict() for item in self.documents],
            "issues": [item.as_dict() for item in self.issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        state = "PASS" if self.passed else "FAIL"
        lines = [
            f"[{state}] suite {self.manifest} tier={self.tier}",
            f"documents={len(self.documents)} body_pages="
            f"{self.total_body_pages}/{self.minimum_total_body_pages} errors={len(self.errors)}",
        ]
        for item in self.documents:
            mark = "PASS" if item.passed else "FAIL"
            lines.append(
                f"- {mark} {item.document_type}: body_pages="
                f"{item.body_pages}/{item.minimum_body_pages}"
            )
        for issue in self.issues:
            scope = f" {issue.document_type}" if issue.document_type else ""
            lines.append(f"- {issue.severity} {issue.code}:{scope} {issue.message}")
        return "\n".join(lines)


def _add(
    report: SuiteAuditReport,
    severity: str,
    code: str,
    message: str,
    document_type: str | None = None,
) -> None:
    report.issues.append(SuiteIssue(severity, code, message, document_type))


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise SuiteError(f"无法读取 YAML {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SuiteError(f"YAML 根节点必须是映射：{path}")
    return value


def _project_mapping(value: str | Path | dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return _load_yaml(Path(value))


def _inject_front_matter(
    text: str,
    *,
    code: str,
    tier: str,
    min_body_pages: int,
    document_id: str,
) -> str:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if match:
        metadata = yaml.safe_load(match.group(1)) or {}
        if not isinstance(metadata, dict):
            metadata = {}
        body = text[match.end():]
    else:
        metadata = {}
        body = text
    document = metadata.setdefault("document", {})
    if not isinstance(document, dict):
        document = metadata["document"] = {}
    document.update({"type": code, "id": document_id, "status": "draft"})
    quality = metadata.setdefault("quality", {})
    if not isinstance(quality, dict):
        quality = metadata["quality"] = {}
    quality.update(
        {
            "tier": tier,
            "min_body_pages": min_body_pages,
            "fixture": False,
            "review_state": "draft",
        }
    )
    return (
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip()
        + "\n---\n"
        + body.lstrip("\n")
    )


def initialize_suite(
    output: str | Path,
    *,
    project: str | Path | dict[str, Any] | None = None,
    tier: str = "large",
    min_body_pages: int | None = None,
    suite_id: str | None = None,
) -> Path:
    import copy
    import os
    import tempfile
    target = Path(output).resolve()
    if target.exists():
        raise SuiteError(f"refusing to overwrite existing workspace: {target}")
    project_data = copy.deepcopy(_project_mapping(project))
    probe = parse_project_tier(project_data)
    normalized_tier = normalize_tier(tier)
    if probe and VALID_TIERS.index(normalized_tier) < VALID_TIERS.index(probe):
        raise SuiteError("suite tier cannot lower project tier")
    quality = project_data.get('quality') or {}
    if not isinstance(quality, dict):
        raise SuiteError('quality must be a mapping')
    overrides = [v for v in (min_body_pages, quality.get('min_body_pages')) if v is not None]
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in overrides):
        raise SuiteError('page targets must be positive integers')
    requested = max(overrides) if overrides else None
    identity = suite_id or str((project_data.get('project') or {}).get('id') or 'GJB438C-SUITE')
    # Compute and validate all templates before making anything visible.
    contents, entries = {}, {}
    for item in iter_document_types():
        code = item.code
        floor = max(minimum_body_pages(code, normalized_tier), requested or 0)
        title = item.chinese_name.replace('/', '-')
        stem = f'[{item.number:02d}][{code}] {title}'
        per_document = copy.deepcopy(project_data)
        per_document.setdefault('document', {}).update(type=code, title=item.chinese_name)
        skeleton = render_skeleton(document_type=item, outline=heading_outline(code), project=per_document)
        contents[f'docs/{stem}.md'] = _inject_front_matter(
            skeleton, code=code, tier=normalized_tier, min_body_pages=floor, document_id=f'{identity}-{code}')
        entries[code] = {'markdown': f'docs/{stem}.md', 'docx': f'dist/{stem}.docx',
                         'volume_report': f'reports/{code}-volume.json', 'min_body_pages': floor}
    manifest = {'schema_version': 1, 'suite': {'id': identity, 'tier': normalized_tier,
                'status': 'draft', 'required_documents': list(entries), 'min_body_pages_each': requested,
                'tailoring': {}, 'page_floor_is_project_policy': True}, 'documents': entries}
    contents['suite.yaml'] = yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.gjb-suite-', dir=target.parent) as folder:
        stage = Path(folder) / 'workspace'; stage.mkdir()
        for directory in ('docs', 'dist', 'reports', 'sources', 'working-baselines'):
            (stage / directory).mkdir()
        for name, text in contents.items():
            (stage / name).write_text(text, encoding='utf-8')
        if target.exists():
            raise SuiteError('workspace appeared during initialization; refusing overwrite')
        # rename fails on an existing non-empty directory; no existing file is overwritten.
        os.rename(stage, target)
    return target / 'suite.yaml'


def parse_project_tier(project):
    values = []
    for key in ('quality', 'project'):
        value = project.get(key) or {}
        if not isinstance(value, dict):
            raise SuiteError(f'{key} must be a mapping')
        values.extend(normalize_tier(value[k]) for k in ('tier', 'scale') if value.get(k))
    return max(values, key=VALID_TIERS.index) if values else None


def _resolve(base: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise SuiteError(f"{label} 缺少路径")
    path = Path(value.strip())
    return path if path.is_absolute() else (base / path).resolve()


def _doc_status(document: MarkdownDocument) -> str:
    value = document.metadata.get("document")
    if isinstance(value, dict):
        return str(value.get("status", "")).strip().lower()
    return ""


def _cross_reference_issues(
    report: SuiteAuditReport,
    documents: dict[str, MarkdownDocument],
) -> None:
    from .references import reference_issues
    for code, document in documents.items():
        for issue in reference_issues(code, document, documents):
            _add(report, issue["severity"], issue["code"], issue["message"], code)


def audit_suite_manifest(
    manifest: str | Path, *, audit_profile: str = "release",
    tier: str | None = None, write_volume_reports: bool = False,
) -> SuiteAuditReport:
    from .trust import approval_issues, filled, valid_date
    from .volume import markdown_volume_issues, resolve_tier
    from .publication import write_report

    if audit_profile not in {"review", "release"}:
        raise SuiteError("suite profile must be review or release")
    manifest_path = Path(manifest).resolve()
    from .publication import distinct_paths
    distinct_paths(manifest_artifact_paths(manifest_path))
    data = _load_yaml(manifest_path)
    suite, raw_entries = data.get("suite"), data.get("documents")
    if not isinstance(suite, dict) or not isinstance(raw_entries, dict):
        raise SuiteError("manifest must contain suite and documents mappings")
    declared_tier = normalize_tier(suite.get("tier") or "large")
    normalized_tier = normalize_tier(tier or declared_tier)
    if VALID_TIERS.index(normalized_tier) < VALID_TIERS.index(declared_tier):
        raise SuiteError('explicit tier cannot lower suite tier')
    report = SuiteAuditReport(manifest_path, normalized_tier)
    entries = {}
    for key, value in raw_entries.items():
        code = get_document_type(str(key)).code
        if code in entries:
            raise SuiteError(f"duplicate document code: {code}")
        entries[code] = value
    all_codes = {item.code for item in iter_document_types()}
    raw_required = suite.get("required_documents", sorted(all_codes))
    if not isinstance(raw_required, list) or not raw_required:
        raise SuiteError("required_documents must be a nonempty list")
    required = [get_document_type(str(x)).code for x in raw_required]
    if len(set(required)) != len(required):
        raise SuiteError("duplicate required_documents")
    tailoring = suite.get("tailoring") or {}
    if not isinstance(tailoring, dict):
        raise SuiteError("suite.tailoring must be a mapping")
    for code in sorted(all_codes - set(required)):
        decision = tailoring.get(code, {})
        if (not isinstance(decision, dict) or decision.get("status") != "approved"
                or not all(filled(decision.get(k)) for k in ("rationale", "impact", "source_refs", "approved_by"))
                or not valid_date(decision.get("approved_at"))):
            _add(report, "ERROR", "SUITE_TAILORING_NOT_APPROVED", "omitted document needs an approved applicability decision", code)
    documents, paths = {}, {}
    for code in required:
        entry = entries.get(code)
        if not isinstance(entry, dict):
            _add(report, "ERROR", "SUITE_DOCUMENT_MISSING", "no selected document entry", code)
            continue
        try:
            path = _resolve(manifest_path.parent, entry.get("markdown"), code + ".markdown")
            if not path.is_file():
                raise SuiteError(f"missing Markdown: {path}")
            paths[code] = path
            documents[code] = parse_markdown(path)
        except (SuiteError, OSError, ValueError) as exc:
            _add(report, "ERROR", "SUITE_MARKDOWN_MISSING", str(exc), code)
    identities = set()
    for code, document in documents.items():
        software = document.metadata.get('software')
        if not isinstance(software, dict):
            _add(report, 'ERROR', 'SUITE_SOFTWARE_METADATA_INVALID', 'software must be a mapping', code)
            identities.add('')
        else:
            identities.add(str(software.get('identifier') or ''))
    if len(identities) != 1 or not all(identities):
        _add(report, 'ERROR', 'SUITE_IDENTITY_MISMATCH', 'selected documents must belong to one software identifier')
    candidates = set()
    for code in required:
        entry = entries.get(code, {})
        if not isinstance(entry, dict):
            entry = {}
        result = SuiteDocumentResult(code, str(paths.get(code, "")), str(entry.get("docx", "")), str(entry.get("volume_report", "")))
        report.documents.append(result)
        document = documents.get(code)
        if document is None:
            continue
        before = len(report.errors)
        try:
            selected_tier = resolve_tier(document, normalized_tier)
            overrides = [entry.get("min_body_pages"), suite.get("min_body_pages_each"), (document.metadata.get("quality") or {}).get("min_body_pages")]
            floors = [minimum_body_pages(code, selected_tier, v) for v in overrides if v is not None]
            floor = max([minimum_body_pages(code, selected_tier), *floors])
        except (ValueError, VolumeError, ProfileQualityError) as exc:
            _add(report, "ERROR", "SUITE_PAGE_OVERRIDE_INVALID", str(exc), code)
            continue
        result.minimum_body_pages = floor
        report.minimum_total_body_pages += floor
        if document_type_from_metadata(document) != code.upper():
            _add(report, "ERROR", "SUITE_TYPE_MISMATCH", "Markdown type differs from manifest", code)
        baseline = paths.get("SRS" if code == "SDD" else "SSS") if code in {"SDD", "SSDD"} else None
        combined = audit_markdown_with_profile(paths[code], profile=audit_profile, document_type=code, baseline_srs=baseline, tier=selected_tier)
        if not combined.passed:
            _add(report, "ERROR", "SUITE_MARKDOWN_AUDIT_FAILED", combined.to_text(), code)
        for issue in markdown_volume_issues(document, code, selected_tier, audit_profile, min_body_pages_override=floor):
            _add(report, issue["severity"], issue["code"], issue["message"], code)
        if audit_profile == "release":
            try:
                docx_path = _resolve(manifest_path.parent, entry.get("docx"), code + ".docx")
                volume_path = _resolve(manifest_path.parent, entry.get("volume_report"), code + ".volume_report")
                docx_report = audit_docx(docx_path, profile="release")
                if not docx_report.passed:
                    _add(report, "ERROR", "SUITE_DOCX_AUDIT_FAILED", docx_report.to_text(), code)
                volume = audit_rendered_volume(document, code, docx_path, tier=selected_tier, min_body_pages_override=floor)
                result.body_pages = volume.body_pages
                report.total_body_pages += volume.body_pages
                if not volume.passed:
                    _add(report, "ERROR", "SUITE_VOLUME_AUDIT_FAILED", volume.to_text(), code)
                if write_volume_reports:
                    write_report(volume_path, volume.to_json(), inputs=[paths[code], docx_path, manifest_path])
                persisted = json.loads(volume_path.read_text(encoding="utf-8"))
                if (persisted.get("passed") is not True or persisted.get("source_sha256") != sha256_file(paths[code])
                        or persisted.get("docx_sha256") != sha256_file(docx_path)
                        or persisted.get("tier") != selected_tier or persisted.get("document_type") != code):
                    _add(report, "ERROR", "SUITE_REPORT_MISMATCH", "volume report is missing current successful evidence", code)
            except (OSError, ValueError, VolumeError, SuiteError) as exc:
                _add(report, "ERROR", "SUITE_RELEASE_AUDIT_FAILED", str(exc), code)
        result.passed = len(report.errors) == before
        if result.passed:
            candidates.add(code)

    # Construct from successful results only, in dependency order. A leftover
    # manifest key, failed document, or dependency cycle cannot seed this set.
    if any(e.document_type is None for e in report.errors):
        candidates.clear()
    usable = set()
    while True:
        previous = set(usable)
        for code in sorted(candidates - usable):
            deps = load_profile_mapping(code).get("baselines", {})
            must = {get_document_type(str(x)).code for x in deps.get("required", [])}
            any_of = {get_document_type(str(x)).code for x in deps.get("required_any", [])}
            if must <= usable and (not any_of or any_of & usable):
                usable.add(code)
        if usable == previous:
            break
    for result in report.documents:
        if result.document_type not in usable:
            result.passed = False
            _add(report, "ERROR", "SUITE_REQUIRED_BASELINE_NOT_AUDITED", "document or its required baseline failed this audit run", result.document_type)
    # Re-evaluate reference scope whenever a failed baseline is removed. This
    # also prevents a required_any fallback from retaining checks against the
    # previously selected (now failed) baseline.
    while True:
        previous = set(usable)
        _cross_reference_issues(report, {code: documents[code] for code in usable})
        usable -= {e.document_type for e in report.errors if e.document_type}
        for code in list(usable):
            deps = load_profile_mapping(code).get("baselines", {})
            must = {get_document_type(str(x)).code for x in deps.get("required", [])}
            any_of = {get_document_type(str(x)).code for x in deps.get("required_any", [])}
            if not must <= usable or (any_of and not any_of & usable):
                usable.remove(code)
                _add(report, "ERROR", "SUITE_REQUIRED_BASELINE_NOT_AUDITED",
                     "a selected baseline failed reference/coverage validation", code)
        if previous == usable:
            break
    for result in report.documents:
        if any(e.document_type in {None, result.document_type} for e in report.errors):
            result.passed = False
    requested = suite.get("min_portfolio_body_pages")
    if requested is not None:
        if isinstance(requested, bool) or not isinstance(requested, int) or requested < report.minimum_total_body_pages:
            _add(report, "ERROR", "SUITE_PORTFOLIO_FLOOR_CANNOT_LOWER", "invalid portfolio page floor")
        else:
            report.minimum_total_body_pages = requested
    if audit_profile == "release" and report.total_body_pages < report.minimum_total_body_pages:
        _add(report, "ERROR", "SUITE_PORTFOLIO_BODY_PAGES_LOW", "rendered portfolio below required body pages")
    return report


def manifest_artifact_paths(manifest):
    path = Path(manifest).resolve()
    data = _load_yaml(path)
    entries = data.get('documents') or {}
    if not isinstance(entries, dict):
        raise SuiteError('documents must be a mapping')
    result = [path]
    for entry in entries.values():
        if not isinstance(entry, dict):
            raise SuiteError('document entry must be a mapping')
        for key in ('markdown', 'docx', 'volume_report'):
            if entry.get(key):
                result.append(_resolve(path.parent, entry[key], key))
    return result
