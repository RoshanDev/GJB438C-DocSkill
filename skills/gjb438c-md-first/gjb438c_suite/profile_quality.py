from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field, is_dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any, Iterable

import yaml

from .markdown_doc import MarkdownDocument, parse_markdown
from .quality import audit_markdown
from .registry import get_document_type
from .trust import filled, approval_issues, tailoring_minimum
import hashlib
from collections import Counter

PROFILE_DIR = Path(__file__).resolve().parent / "data" / "profiles"
TIER_ALIASES = {
    "prototype": "prototype",
    "proto": "prototype",
    "small": "standard",
    "standard": "standard",
    "medium": "large",
    "large": "large",
    "very-large": "critical",
    "very_large": "critical",
    "critical": "critical",
}
VALID_TIERS = ("prototype", "standard", "large", "critical")


class ProfileQualityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProfileIssue:
    severity: str
    code: str
    message: str
    line: int | None = None
    artifact_kind: str | None = None
    artifact_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ProfileAuditReport:
    document_type: str
    tier: str
    audit_profile: str
    issues: list[ProfileIssue] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    minimums: dict[str, int] = field(default_factory=dict)
    heading_coverage_percent: float = 0.0

    @property
    def errors(self) -> list[ProfileIssue]:
        return [item for item in self.issues if item.severity == "ERROR"]

    @property
    def passed(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_type": self.document_type,
            "tier": self.tier,
            "audit_profile": self.audit_profile,
            "passed": self.passed,
            "summary": {
                "errors": len(self.errors),
                "warnings": sum(1 for item in self.issues if item.severity == "WARN"),
                "heading_coverage_percent": round(self.heading_coverage_percent, 2),
            },
            "counts": self.counts,
            "minimums": self.minimums,
            "issues": [item.as_dict() for item in self.issues],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        state = "PASS" if self.passed else "FAIL"
        lines = [
            f"[{state}] profile {self.document_type} tier={self.tier} "
            f"headings={self.heading_coverage_percent:.2f}% errors={len(self.errors)}"
        ]
        for item in self.issues:
            where = ""
            if item.artifact_kind:
                where += f" kind={item.artifact_kind}"
            if item.artifact_id:
                where += f" id={item.artifact_id}"
            if item.line:
                where += f" line={item.line}"
            lines.append(f"- {item.severity} {item.code}:{where} {item.message}")
        return "\n".join(lines)


@dataclass(slots=True)
class CombinedAuditReport:
    generic: Any
    profile: ProfileAuditReport

    @property
    def passed(self) -> bool:
        return bool(getattr(self.generic, "passed", False)) and self.profile.passed

    def as_dict(self) -> dict[str, Any]:
        try:
            generic = json.loads(self.generic.to_json())
        except Exception:
            generic = {
                "passed": bool(getattr(self.generic, "passed", False)),
                "text": self.generic.to_text(),
            }
        return {
            "passed": self.passed,
            "generic": generic,
            "profile": self.profile.as_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)

    def to_text(self) -> str:
        return f"{self.generic.to_text()}\n{self.profile.to_text()}"


def normalize_tier(value: str | None) -> str:
    key = str(value or "prototype").strip().lower().replace(" ", "-")
    try:
        return TIER_ALIASES[key]
    except KeyError as exc:
        raise ProfileQualityError(
            f"tier/scale 必须是 {', '.join(VALID_TIERS)}；实际为 {value!r}"
        ) from exc


@lru_cache(maxsize=None)
def _load_profile_mapping_cached(code: str) -> dict[str, Any]:
    normalized = str(code).strip().upper()
    path = PROFILE_DIR / f"{normalized.lower()}.yaml"
    if not path.is_file():
        raise ProfileQualityError(f"找不到内置 Profile：{normalized} ({path})")
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ProfileQualityError(f"Profile 必须是 YAML 映射：{path}")
    if str(value.get("code", "")).upper() != normalized:
        raise ProfileQualityError(f"Profile code 不一致：{path}")
    return value


def load_profile_mapping(code: str) -> dict[str, Any]:
    """每次返回新的深拷贝，调用方不能污染后续审计。"""
    value = deepcopy(_load_profile_mapping_cached(str(code).strip().upper()))
    value["code"] = get_document_type(code).code
    return value


def tier_minimum(value: Any, tier: str, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if isinstance(value, dict):
        normalized = normalize_tier(tier)
        if normalized in value:
            return max(0, int(value[normalized]))
        for alias, canonical in TIER_ALIASES.items():
            if canonical == normalized and alias in value:
                return max(0, int(value[alias]))
        raise ProfileQualityError(
            f"Profile minimum 缺少 tier={normalized}；可用键={sorted(value)}"
        )
    if value is None:
        return max(0, int(default))
    raise ProfileQualityError(f"无效 minimum：{value!r}")


def resolve_document_tier(document: MarkdownDocument, explicit: str | None = None) -> str:
    declared = []
    for container in (document.metadata.get("quality"), document.metadata.get("project")):
        if isinstance(container, dict):
            declared += [normalize_tier(str(container[k])) for k in ("tier", "scale") if container.get(k)]
    if explicit:
        selected = normalize_tier(explicit)
        if declared and VALID_TIERS.index(selected) < max(VALID_TIERS.index(x) for x in declared):
            raise ProfileQualityError("explicit tier cannot lower the declared project tier")
        return selected
    if declared:
        return max(declared, key=VALID_TIERS.index)
    for container_name in ("quality", "project"):
        container = document.metadata.get(container_name)
        if not isinstance(container, dict):
            continue
        for key in ("tier", "scale"):
            if container.get(key):
                return normalize_tier(str(container[key]))
    return "prototype"


def has_declared_tier(document: MarkdownDocument, explicit: str | None = None) -> bool:
    if explicit:
        return True
    for container_name in ("quality", "project"):
        container = document.metadata.get(container_name)
        if isinstance(container, dict) and (container.get("tier") or container.get("scale")):
            return True
    return False


def is_fixture(document: MarkdownDocument) -> bool:
    quality = document.metadata.get("quality")
    return isinstance(quality, dict) and quality.get("fixture") is True


def document_type_from_metadata(document: MarkdownDocument) -> str | None:
    value = document.metadata.get("document")
    if isinstance(value, dict) and value.get("type"):
        return str(value["type"]).strip().upper()
    for key in ("document_type", "type"):
        if document.metadata.get(key):
            return str(document.metadata[key]).strip().upper()
    return None


def artifact_mapping(artifact: Any) -> dict[str, Any]:
    for name in ("data", "payload", "value", "content"):
        value = getattr(artifact, name, None)
        if isinstance(value, dict):
            return value
    if isinstance(artifact, dict):
        return artifact
    if is_dataclass(artifact):
        value = asdict(artifact)
        for name in ("data", "payload", "value", "content"):
            nested = value.get(name)
            if isinstance(nested, dict):
                return nested
        return value
    return {}


def artifact_kind(artifact: Any) -> str:
    value = getattr(artifact, "kind", None)
    if value is None and isinstance(artifact, dict):
        value = artifact.get("kind")
    return str(value or "").strip().lower().removeprefix("gjb-")


def artifact_line(artifact: Any) -> int | None:
    value = getattr(artifact, "line", None)
    if value is None:
        value = getattr(artifact, "start_line", None)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return False


def _normalized_heading(value: str) -> str:
    value = re.sub(r"^\s*\d+(?:\.\d+)*\s*", "", value.strip())
    return re.sub(r"[\s\u3000:：()（）]+", "", value).lower()


def _dynamic_heading(value: str) -> bool:
    compact = value.upper()
    return bool(re.search(r"(?:^|[.\s])X(?:[.\s]|$)|(?:^|[.\s])Y(?:[.\s]|$)", compact))


def _iter_artifacts(document: MarkdownDocument) -> Iterable[Any]:
    value = getattr(document, "artifacts", ())
    return value if isinstance(value, (list, tuple)) else tuple(value or ())


def audit_profile_document(
    source: str | Path | MarkdownDocument,
    *,
    document_type: str | None = None,
    audit_profile: str = "review",
    tier: str | None = None,
) -> ProfileAuditReport:
    document = source if isinstance(source, MarkdownDocument) else parse_markdown(source)
    detected = document_type_from_metadata(document)
    code = str(document_type or detected or "").strip().upper()
    if not code:
        raise ProfileQualityError("无法确定文档类型；需设置 document.type 或 --type")
    mapping = load_profile_mapping(code)
    resolved_tier = resolve_document_tier(document, tier)
    report = ProfileAuditReport(code, resolved_tier, audit_profile)
    severity = "ERROR" if audit_profile in {"review", "release"} else "WARN"

    if detected and detected != code:
        report.issues.append(
            ProfileIssue("ERROR", "PROFILE_TYPE_MISMATCH", f"文档声明 {detected}，实际按 {code} 审计")
        )
    if audit_profile == "release" and not has_declared_tier(document, tier):
        report.issues.append(
            ProfileIssue("ERROR", "PROFILE_TIER_REQUIRED", "发布文档必须显式声明 quality.tier/scale")
        )
    if audit_profile == "release" and resolved_tier == "prototype" :
        report.issues.append(
            ProfileIssue(
                "ERROR",
                "PROFILE_PROTOTYPE_RELEASE_FORBIDDEN",
                "prototype 仅供示例和 CI；生产发布必须使用 standard、large 或 critical",
            )
        )
    allowed = mapping.get("release_rules", {}).get("allowed_tiers", VALID_TIERS)
    allowed = {normalize_tier(str(item)) for item in allowed}
    if audit_profile == "release" and resolved_tier not in allowed:
        report.issues.append(
            ProfileIssue(
                "ERROR",
                "PROFILE_TIER_NOT_ALLOWED",
                f"{code} 不允许以 tier={resolved_tier} 发布；允许值={sorted(allowed)}",
            )
        )

    artifacts = list(_iter_artifacts(document))
    by_kind: dict[str, list[Any]] = {}
    seen_ids: dict[str, tuple[str, int | None]] = {}
    for artifact in artifacts:
        kind = artifact_kind(artifact)
        if kind:
            by_kind.setdefault(kind, []).append(artifact)
        payload = artifact_mapping(artifact)
        artifact_id = str(payload.get("id", "")).strip()
        if artifact_id:
            if artifact_id in seen_ids:
                prior_kind, prior_line = seen_ids[artifact_id]
                report.issues.append(
                    ProfileIssue(
                        "ERROR",
                        "PROFILE_DUPLICATE_ID",
                        f"稳定标识重复；首次 kind={prior_kind} line={prior_line}",
                        artifact_line(artifact),
                        kind,
                        artifact_id,
                    )
                )
            else:
                seen_ids[artifact_id] = (kind, artifact_line(artifact))

    contracts = mapping.get("artifact_contracts", [])
    if not isinstance(contracts, list):
        raise ProfileQualityError(f"{code} artifact_contracts 必须是列表")
    for contract in contracts:
        if not isinstance(contract, dict) or not contract.get("kind"):
            continue
        kind = str(contract["kind"]).strip().lower().removeprefix("gjb-")
        items = by_kind.get(kind, [])
        minimum = tier_minimum(contract.get("minimum"), resolved_tier)
        minimum, tailoring_errors = tailoring_minimum(document, kind, minimum)
        for message in tailoring_errors:
            report.issues.append(ProfileIssue(severity, "TAILORING_NOT_APPROVED", message))
        report.counts[kind] = len(items)
        report.minimums[kind] = minimum
        if len(items) < minimum:
            report.issues.append(
                ProfileIssue(
                    severity,
                    "PROFILE_ARTIFACT_COUNT_LOW",
                    f"gjb-{kind} 数量 {len(items)} 低于 {code}/{resolved_tier} 最低值 {minimum}",
                    artifact_kind=kind,
                )
            )
        required_fields = tuple(str(item) for item in contract.get("required_fields", []) if item)
        for artifact in items:
            payload = artifact_mapping(artifact)
            artifact_id = str(payload.get("id", "")).strip() or None
            for field_name in required_fields:
                if not filled(payload.get(field_name)):
                    report.issues.append(
                        ProfileIssue(
                            severity,
                            "PROFILE_REQUIRED_FIELD_MISSING",
                            f"gjb-{kind} 缺少字段 {field_name}",
                            artifact_line(artifact),
                            kind,
                            artifact_id,
                        )
                    )

    expected = []
    for item in mapping.get("outline", []):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if title and not _dynamic_heading(title):
            expected.append((int(item.get("level", 1)), _normalized_heading(title), title))
    actual = {
        _normalized_heading(str(getattr(item, "title", item)))
        for item in getattr(document, "headings", ())
    }
    matched = sum(1 for _, normalized, _ in expected if normalized in actual)
    report.heading_coverage_percent = matched / len(expected) * 100 if expected else 100.0
    for level, normalized, title in expected:
        if normalized in actual:
            continue
        missing_severity = "ERROR" if audit_profile == "release" and level == 1 else severity
        report.issues.append(
            ProfileIssue(
                missing_severity,
                "PROFILE_HEADING_MISSING",
                f"缺少 Profile 章节：{title}",
            )
        )
    source_ids = {s.get("id") for s in document.metadata.get("sources", []) if isinstance(s, dict)}
    for artifact in artifacts:
        refs = artifact.data.get("source_refs", [])
        refs = [refs] if isinstance(refs, str) else refs
        if not isinstance(refs, list):
            report.issues.append(ProfileIssue(severity, "SOURCE_REFS_INVALID", "source_refs must be a list", artifact.line))
            continue
        for ref in refs:
            if str(ref).split("#", 1)[0] not in source_ids:
                report.issues.append(ProfileIssue(severity, "SOURCE_UNKNOWN", str(ref), artifact.line))
    # Exact duplicated payloads are errors. Number/ID normalization is NOT used:
    # distinct boundary-test inputs and performance limits are meaningful.
    for kind, items in by_kind.items():
        values = [json.dumps({k: v for k, v in a.data.items() if k not in {"id", "source_refs", "source"}},
                             sort_keys=True, ensure_ascii=False, default=str) for a in items]
        duplicates = sum(n - 1 for n in Counter(values).values())
        if len(values) >= 5 and duplicates / len(values) > 0.4:
            report.issues.append(ProfileIssue(severity, "DUPLICATE_EVIDENCE", f"{kind}: {duplicates}/{len(values)} duplicated payloads"))
    if audit_profile == "release" or document.metadata.get("document", {}).get("status") in {"approved", "released"}:
        for message in approval_issues(document):
            report.issues.append(ProfileIssue("ERROR", "APPROVAL_INVALID", message))
    return report


def audit_markdown_with_profile(
    source: str | Path,
    *,
    profile: str = "review",
    document_type: str | None = None,
    baseline_srs: str | Path | None = None,
    tier: str | None = None,
    scale: str | None = None,
) -> CombinedAuditReport:
    generic = audit_markdown(
        source,
        profile=profile,
        document_type=document_type,
        baseline_srs=baseline_srs,
    )
    specific = audit_profile_document(
        source,
        document_type=document_type,
        audit_profile=profile,
        tier=tier or scale,
    )
    return CombinedAuditReport(generic, specific)
