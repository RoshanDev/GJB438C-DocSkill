from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import re
from typing import Any, Iterable

from .markdown_doc import Artifact, MarkdownDocument, nested_get, parse_markdown
from .registry import DocumentType, get_document_type

PROFILE_LEVEL = {"draft": 0, "review": 1, "release": 2}
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{2,127}$")
VAGUE_ACCEPTANCE_RE = re.compile(
    r"^(?:正常|正确|合理|友好|高效|满足要求|按需|适当|尽快|无异常|成功)[。.]?$", re.I
)
PLACEHOLDER_VALUE_RE = re.compile(r"(?:待提供|待测试执行|待补充|待确认|待定|\bTBD\b|\bTODO\b|XXXX+)", re.I)


@dataclass(slots=True)
class Issue:
    severity: str
    code: str
    message: str
    line: int | None = None
    artifact_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "line": self.line,
            "artifact_id": self.artifact_id,
        }


@dataclass(slots=True)
class AuditReport:
    path: Path
    document_type: str | None
    profile: str
    issues: list[Issue] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "WARN"]

    @property
    def passed(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "document_type": self.document_type,
            "profile": self.profile,
            "passed": self.passed,
            "summary": {"errors": len(self.errors), "warnings": len(self.warnings)},
            "metrics": self.metrics,
            "issues": [issue.as_dict() for issue in self.issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        state = "PASS" if self.passed else "FAIL"
        lines = [
            f"[{state}] {self.path} ({self.document_type or 'UNKNOWN'}, profile={self.profile})",
            f"errors={len(self.errors)} warnings={len(self.warnings)} metrics={self.metrics}",
        ]
        for issue in self.issues:
            location = f" line={issue.line}" if issue.line else ""
            artifact = f" artifact={issue.artifact_id}" if issue.artifact_id else ""
            lines.append(f"- {issue.severity} {issue.code}:{location}{artifact} {issue.message}")
        return "\n".join(lines)


def _add(
    report: AuditReport,
    severity: str,
    code: str,
    message: str,
    *,
    line: int | None = None,
    artifact: Artifact | None = None,
) -> None:
    report.issues.append(
        Issue(
            severity,
            code,
            message,
            line or (artifact.line if artifact else None),
            artifact.identifier if artifact else None,
        )
    )


def _severity(profile: str, *, review_error: bool = False, release_error: bool = True) -> str:
    if review_error and PROFILE_LEVEL[profile] >= 1:
        return "ERROR"
    if release_error and PROFILE_LEVEL[profile] >= 2:
        return "ERROR"
    return "WARN"


def _is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not PLACEHOLDER_VALUE_RE.search(value)
    if isinstance(value, (list, tuple, dict, set)):
        if not value:
            return False
        return all(_is_nonempty(item) for item in value) if not isinstance(value, dict) else True
    return True


def _values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _reference_root(value: str) -> str:
    return value.strip().split("#", 1)[0].strip()


def _source_catalog(doc: MarkdownDocument, report: AuditReport) -> set[str]:
    profile = report.profile
    sources = doc.metadata.get("sources")
    if not isinstance(sources, list) or not sources:
        _add(report, _severity(profile), "SOURCE_CATALOG_MISSING", "sources 必须包含至少一条来源记录")
        return set()
    result: set[str] = set()
    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            _add(report, _severity(profile), "SOURCE_INVALID", f"第 {index} 条来源不是对象")
            continue
        source_id = str(source.get("id", "")).strip()
        if not source_id or not ID_RE.fullmatch(source_id):
            _add(report, _severity(profile), "SOURCE_ID_INVALID", f"第 {index} 条来源缺少稳定 id")
            continue
        if source_id in result:
            _add(report, "ERROR", "SOURCE_ID_DUPLICATE", f"来源标识 {source_id} 重复")
        result.add(source_id)
        for key in ("path", "version"):
            if not _is_nonempty(source.get(key)):
                _add(report, _severity(profile), "SOURCE_FIELD_MISSING", f"来源 {source_id} 缺少 {key}")
    return result


def _audit_source_references(
    doc: MarkdownDocument,
    report: AuditReport,
    source_ids: set[str],
    artifact_ids: set[str],
) -> None:
    severity = _severity(report.profile, review_error=True)
    for artifact in doc.artifacts:
        references: list[str] = []
        if artifact.kind == "requirement":
            references.extend(_values(artifact.data.get("source")))
        references.extend(_values(artifact.data.get("source_refs")))
        for reference in references:
            root = _reference_root(reference)
            if root in source_ids or root in artifact_ids:
                continue
            _add(
                report,
                severity,
                "SOURCE_REF_UNKNOWN",
                f"来源引用 {reference!r} 未在 sources 或结构化证据标识中定义",
                artifact=artifact,
            )


def _audit_id_references(
    report: AuditReport,
    artifact: Artifact,
    field: str,
    allowed_ids: set[str],
    *,
    allow_namespaced: bool = False,
) -> set[str]:
    values = set(_values(artifact.data.get(field)))
    for value in sorted(values):
        candidate = value.split(":", 1)[-1] if allow_namespaced and ":" in value else value
        if candidate not in allowed_ids:
            _add(
                report,
                _severity(report.profile, review_error=True),
                "REFERENCE_UNKNOWN",
                f"{artifact.kind}.{field} 引用了不存在的标识 {value}",
                artifact=artifact,
            )
    return values


def _require_fields(
    report: AuditReport,
    artifact: Artifact,
    fields: Iterable[str],
    profile: str,
    *,
    review_error: bool = False,
) -> None:
    for name in fields:
        if not _is_nonempty(artifact.data.get(name)):
            _add(
                report,
                _severity(profile, review_error=review_error),
                "ARTIFACT_FIELD_MISSING",
                f"{artifact.kind} 缺少有效字段 {name}",
                artifact=artifact,
            )


def _audit_common(doc: MarkdownDocument, item: DocumentType, report: AuditReport) -> tuple[set[str], set[str]]:
    profile = report.profile
    for message in doc.parse_errors:
        _add(report, "ERROR", "MARKDOWN_PARSE", message)

    required_meta = (
        "document.type",
        "document.title",
        "document.id",
        "document.version",
        "document.status",
        "software.name",
        "software.version",
        "software.identifier",
        "organization",
        "classification",
        "date",
        "front_matter.template",
        "front_matter.archive_id",
        "front_matter.project_code",
        "front_matter.phase",
        "front_matter.date_cn",
    )
    for key in required_meta:
        if not _is_nonempty(nested_get(doc.metadata, key)):
            _add(report, _severity(profile), "METADATA_MISSING", f"缺少有效元数据 {key}")

    declared_type = str(nested_get(doc.metadata, "document.type", "")).strip()
    if declared_type:
        try:
            declared_code = get_document_type(declared_type).code
        except ValueError:
            declared_code = declared_type.upper()
        if declared_code != item.code:
            _add(
                report,
                "ERROR",
                "TYPE_MISMATCH",
                f"front matter 声明 {declared_type}，实际审计类型为 {item.code}",
            )

    signatures = doc.metadata.get("signatures")
    if not isinstance(signatures, dict):
        _add(report, _severity(profile), "SIGNATURES_INVALID", "signatures 必须是对象")
    else:
        for key in ("prepared", "reviewed", "standard_reviewed", "countersigned", "approved"):
            if key not in signatures:
                _add(report, _severity(profile), "SIGNATURE_ROLE_MISSING", f"签字页缺少 {key}")

    revisions = doc.metadata.get("revisions")
    if not isinstance(revisions, list) or not revisions:
        _add(report, _severity(profile), "REVISION_MISSING", "变更履历缺少修订记录")
    else:
        for index, row in enumerate(revisions, 1):
            if not isinstance(row, dict) or not all(
                _is_nonempty(row.get(key)) for key in ("date", "version", "description", "author")
            ):
                _add(report, _severity(profile), "REVISION_INCOMPLETE", f"第 {index} 条修订记录不完整")

    if len(doc.headings) < 3:
        _add(report, _severity(profile), "OUTLINE_TOO_SHALLOW", "正文标题少于 3 个，疑似未按模板展开")

    if doc.placeholders:
        severity = "ERROR" if profile == "release" else "WARN"
        for placeholder in doc.placeholders[:50]:
            _add(
                report,
                severity,
                "PLACEHOLDER",
                f"残留占位内容：{placeholder.text}",
                line=placeholder.line,
            )
        if len(doc.placeholders) > 50:
            _add(
                report,
                severity,
                "PLACEHOLDER_TRUNCATED",
                f"另有 {len(doc.placeholders) - 50} 处占位内容未逐条列出",
            )

    source_ids = _source_catalog(doc, report)
    ids: dict[str, Artifact] = {}
    kinds = {artifact.kind for artifact in doc.artifacts}
    for artifact in doc.artifacts:
        if not artifact.identifier:
            _add(
                report,
                _severity(profile),
                "ARTIFACT_ID_MISSING",
                f"{artifact.kind} 数据块缺少 id",
                artifact=artifact,
            )
            continue
        if not ID_RE.fullmatch(artifact.identifier):
            _add(
                report,
                _severity(profile),
                "ARTIFACT_ID_INVALID",
                f"标识 {artifact.identifier!r} 不稳定或格式非法",
                artifact=artifact,
            )
        if artifact.identifier in ids:
            _add(
                report,
                "ERROR",
                "ARTIFACT_ID_DUPLICATE",
                f"标识 {artifact.identifier} 重复",
                artifact=artifact,
            )
        else:
            ids[artifact.identifier] = artifact

        if profile == "release" and artifact.kind not in {"requirement", "traceability"}:
            if not _is_nonempty(artifact.data.get("source_refs")):
                _add(
                    report,
                    "ERROR",
                    "SOURCE_REF_MISSING",
                    f"{artifact.kind} 缺少 source_refs，结论无来源证据",
                    artifact=artifact,
                )
            substantive = [
                value
                for key, value in artifact.data.items()
                if key not in {"id", "title", "kind", "source_refs"} and _is_nonempty(value)
            ]
            if not substantive:
                _add(
                    report,
                    "ERROR",
                    "ARTIFACT_EMPTY",
                    f"{artifact.kind} 只有标识/来源，没有实质内容",
                    artifact=artifact,
                )

    from .profiles import artifact_contracts_for
    for kind in (item.required_artifacts if item.code == "SRS" else tuple(c["kind"] for c in artifact_contracts_for(item.code))):
        if kind not in kinds:
            _add(
                report,
                _severity(profile),
                "ARTIFACT_KIND_MISSING",
                f"缺少质量门禁数据块 gjb-{kind}",
            )

    artifact_ids = set(ids)
    _audit_source_references(doc, report, source_ids, artifact_ids)
    report.metrics.update(
        {
            "headings": len(doc.headings),
            "artifacts": len(doc.artifacts),
            "artifact_kinds": sorted(kinds),
            "placeholders": len(doc.placeholders),
            "sources": len(source_ids),
        }
    )
    return source_ids, artifact_ids


def _audit_srs(doc: MarkdownDocument, report: AuditReport) -> set[str]:
    profile = report.profile
    requirements = doc.artifacts_of("requirement")
    requirement_ids: set[str] = set()
    for requirement in requirements:
        _require_fields(
            report,
            requirement,
            ("id", "statement", "rationale", "source", "priority", "verification", "acceptance"),
            profile,
            review_error=True,
        )
        if requirement.identifier:
            requirement_ids.add(requirement.identifier)
        statement = str(requirement.data.get("statement", ""))
        if statement and "应" not in statement:
            _add(
                report,
                _severity(profile, review_error=True),
                "REQUIREMENT_NORMATIVE_WORD",
                "需求陈述应使用“应”表达可验证义务",
                artifact=requirement,
            )
        acceptance = _values(requirement.data.get("acceptance"))
        if acceptance and all(VAGUE_ACCEPTANCE_RE.fullmatch(value) for value in acceptance):
            _add(
                report,
                _severity(profile, review_error=True),
                "ACCEPTANCE_VAGUE",
                "验收准则仅含模糊词，缺少条件、动作与可观察结果",
                artifact=requirement,
            )
        verification = {value.lower() for value in _values(requirement.data.get("verification"))}
        allowed = {"test", "analysis", "inspection", "demonstration", "测试", "分析", "检查", "演示"}
        if verification and not verification.intersection(allowed):
            _add(
                report,
                "WARN",
                "VERIFICATION_METHOD_UNKNOWN",
                f"未识别的验证方法：{sorted(verification)}",
                artifact=requirement,
            )
    if not requirements:
        _add(report, _severity(profile, review_error=True), "SRS_NO_REQUIREMENT", "SRS 未包含任何 gjb-requirement 数据块")

    traces = doc.artifacts_of("traceability")
    traced: set[str] = set()
    if not traces:
        _add(report, _severity(profile, review_error=True), "TRACEABILITY_MISSING", "SRS 缺少 gjb-traceability 数据块")
    for trace in traces:
        _require_fields(report, trace, ("id", "source_refs", "requirements", "forward_targets"), profile, review_error=True)
        traced.update(_values(trace.data.get("requirements")))
    for requirement_id in sorted(requirement_ids - traced):
        _add(report, _severity(profile, review_error=True), "SRS_REQUIREMENT_UNTRACED", f"需求 {requirement_id} 未进入追踪数据块")
    for requirement_id in sorted(traced - requirement_ids):
        _add(report, "WARN" if profile == "draft" and bool(PLACEHOLDER_VALUE_RE.search(requirement_id)) else "ERROR", "SRS_TRACE_UNKNOWN_REQUIREMENT", f"追踪数据块引用了不存在的需求 {requirement_id}")

    report.metrics["requirements"] = len(requirements)
    report.metrics["traced_requirements"] = len(traced & requirement_ids)
    return requirement_ids


def _load_baseline_requirements(path: str | Path, report: AuditReport) -> set[str]:
    baseline_path = Path(path)
    if not baseline_path.is_file():
        _add(report, "ERROR", "BASELINE_SRS_MISSING", f"找不到 SRS 基线：{baseline_path}")
        return set()
    baseline = parse_markdown(baseline_path)
    ids = {
        artifact.identifier
        for artifact in baseline.artifacts_of("requirement")
        if artifact.identifier
    }
    if not ids:
        _add(report, "ERROR", "BASELINE_SRS_EMPTY", f"SRS 基线中没有结构化需求：{baseline_path}")
    return ids


def _audit_sdd(
    doc: MarkdownDocument,
    report: AuditReport,
    baseline_srs: str | Path | None,
) -> None:
    profile = report.profile
    specs: dict[str, tuple[str, ...]] = {
        "decision": ("id", "context", "options", "decision", "rationale", "consequences", "status", "source_refs"),
        "architecture": ("id", "components", "connectors", "deployment", "failure_domains", "source_refs"),
        "design-unit": (
            "id", "requirements", "responsibility", "behavior", "interfaces", "data", "states",
            "errors", "concurrency", "security", "deployment", "verification", "source_refs",
        ),
        "interface": (
            "id", "provider", "consumer", "protocol", "input", "output", "timing", "errors",
            "security", "compatibility", "source_refs",
        ),
        "data": ("id", "owner", "schema", "constraints", "transaction", "retention", "security", "recovery", "source_refs"),
        "scenario": (
            "id", "requirements", "trigger", "preconditions", "steps", "failures", "postconditions",
            "observability", "source_refs",
        ),
        "deployment": ("id", "nodes", "placement", "resources", "network", "storage", "upgrade", "rollback", "source_refs"),
        "security": ("id", "assets", "threats", "controls", "audit", "residual_risk", "source_refs"),
        "verification": ("id", "target", "method", "criteria", "evidence", "source_refs"),
    }
    by_kind = {kind: doc.artifacts_of(kind) for kind in specs}
    for kind, fields in specs.items():
        for artifact in by_kind[kind]:
            _require_fields(report, artifact, fields, profile, review_error=True)

    referenced: set[str] = set()
    for artifact in (*by_kind["design-unit"], *by_kind["scenario"]):
        referenced.update(_values(artifact.data.get("requirements")))

    baseline_ids: set[str] = set()
    if baseline_srs:
        baseline_ids = _load_baseline_requirements(baseline_srs, report)
    elif profile == "release":
        _add(report, "ERROR", "BASELINE_SRS_REQUIRED", "发布 SDD 必须通过 --baseline-srs 指定已审核 SRS")
    else:
        _add(report, "WARN", "BASELINE_SRS_RECOMMENDED", "未指定 SRS 基线，无法验证需求—设计覆盖率")

    if baseline_ids:
        missing = sorted(baseline_ids - referenced)
        unknown = sorted(referenced - baseline_ids)
        for requirement_id in missing:
            _add(
                report,
                "ERROR" if profile in {"review", "release"} else "WARN",
                "SDD_REQUIREMENT_UNCOVERED",
                f"需求 {requirement_id} 未映射到 design-unit/scenario",
            )
        for requirement_id in unknown:
            _add(report, "ERROR", "SDD_REQUIREMENT_UNKNOWN", f"设计引用了 SRS 中不存在的需求 {requirement_id}")
        coverage = len(baseline_ids - set(missing)) / len(baseline_ids) * 100
        report.metrics["requirement_coverage_percent"] = round(coverage, 2)

    interface_ids = {item.identifier for item in by_kind["interface"] if item.identifier}
    data_ids = {item.identifier for item in by_kind["data"] if item.identifier}
    verification_ids = {item.identifier for item in by_kind["verification"] if item.identifier}
    design_unit_ids = {item.identifier for item in by_kind["design-unit"] if item.identifier}
    all_target_ids = {
        artifact.identifier
        for artifact in doc.artifacts
        if artifact.identifier
    }
    referenced_interfaces: set[str] = set()
    referenced_data: set[str] = set()
    referenced_verifications: set[str] = set()
    for unit in by_kind["design-unit"]:
        referenced_interfaces.update(_audit_id_references(report, unit, "interfaces", interface_ids))
        referenced_data.update(_audit_id_references(report, unit, "data", data_ids))
        referenced_verifications.update(_audit_id_references(report, unit, "verification", verification_ids))
    for interface in by_kind["interface"]:
        provider = str(interface.data.get("provider", "")).strip()
        if provider.startswith("DU-") and provider not in design_unit_ids:
            _add(report, _severity(profile, review_error=True), "INTERFACE_PROVIDER_UNKNOWN", f"接口提供者 {provider} 不存在", artifact=interface)

    traces = doc.artifacts_of("traceability")
    traced_requirements: set[str] = set()
    if not traces:
        _add(report, _severity(profile, review_error=True), "TRACEABILITY_MISSING", "SDD 缺少 gjb-traceability 数据块")
    for trace in traces:
        _require_fields(report, trace, ("id", "source_refs", "requirements", "forward_targets"), profile, review_error=True)
        traced_requirements.update(_values(trace.data.get("requirements")))
        _audit_id_references(report, trace, "forward_targets", all_target_ids, allow_namespaced=True)
    if baseline_ids:
        for requirement_id in sorted(baseline_ids - traced_requirements):
            _add(report, _severity(profile, review_error=True), "SDD_REQUIREMENT_UNTRACED", f"需求 {requirement_id} 未进入 SDD 追踪数据块")
        for requirement_id in sorted(traced_requirements - baseline_ids):
            _add(report, "ERROR", "SDD_TRACE_UNKNOWN_REQUIREMENT", f"SDD 追踪数据块引用了不存在的需求 {requirement_id}")

    for orphan in sorted(interface_ids - referenced_interfaces):
        _add(report, "WARN", "INTERFACE_ORPHAN", f"接口 {orphan} 未被任何 design-unit 引用")
    for orphan in sorted(data_ids - referenced_data):
        _add(report, "WARN", "DATA_ORPHAN", f"数据对象 {orphan} 未被任何 design-unit 引用")
    for orphan in sorted(verification_ids - referenced_verifications):
        _add(report, "WARN", "VERIFICATION_ORPHAN", f"验证项 {orphan} 未被任何 design-unit 引用")

    report.metrics.update(
        {
            "design_units": len(by_kind["design-unit"]),
            "interfaces": len(by_kind["interface"]),
            "data_items": len(by_kind["data"]),
            "scenarios": len(by_kind["scenario"]),
            "decisions": len(by_kind["decision"]),
            "traced_requirements": len(traced_requirements & baseline_ids) if baseline_ids else len(traced_requirements),
        }
    )


def _audit_generic(doc: MarkdownDocument, item: DocumentType, report: AuditReport) -> None:
    # For the remaining 16 document kinds, the type-specific `required_artifacts`
    # registry provides the quality floor. Each block must carry an ID and, at
    # release, a source reference plus substantive content.
    counts = {kind: len(doc.artifacts_of(kind)) for kind in item.required_artifacts}
    report.metrics["required_artifact_counts"] = counts


def audit_markdown(
    path: str | Path,
    *,
    profile: str = "review",
    document_type: str | None = None,
    baseline_srs: str | Path | None = None,
) -> AuditReport:
    if profile not in PROFILE_LEVEL:
        raise ValueError("profile 必须是 draft、review 或 release")
    doc = parse_markdown(path)
    declared = document_type or str(nested_get(doc.metadata, "document.type", ""))
    report = AuditReport(Path(path), declared.upper() if declared else None, profile)
    if not declared:
        _add(report, "ERROR", "TYPE_MISSING", "无法确定文档类型；请设置 document.type 或传 --type")
        return report
    try:
        item = get_document_type(declared)
    except ValueError as exc:
        _add(report, "ERROR", "TYPE_UNKNOWN", str(exc))
        return report

    report.document_type = item.code
    _source_ids, _artifact_ids = _audit_common(doc, item, report)
    if item.code in {"SRS", "SSS"}:
        _audit_srs(doc, report)
    elif item.code in {"SDD", "SSDD"}:
        _audit_sdd(doc, report, baseline_srs)
    else:
        _audit_generic(doc, item, report)
    return report
