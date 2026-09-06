"""Explicit approval records and reproducible content fingerprints.

A name in YAML is an assertion, not authentication of a human signature.
Approval must be entered/reviewed by the project owner, never auto-generated.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Any

from .markdown_doc import MarkdownDocument

PENDING = re.compile(r"待(?:提供|补充|确认|定|测试|执行)|\b(?:TODO|TBD)\b|XXXX+|\{\{", re.I)


def filled(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not PENDING.search(value)
    if isinstance(value, dict):
        return bool(value) and all(filled(x) for x in value.values())
    if isinstance(value, (list, tuple)):
        return bool(value) and all(filled(x) for x in value)
    return isinstance(value, (int, float, bool, date))


def fingerprint(document: MarkdownDocument) -> str:
    metadata = deepcopy(document.metadata)
    metadata.pop("approval", None)
    raw = json.dumps(metadata, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256((raw + "\n" + document.body.replace("\r\n", "\n")).encode()).hexdigest()


def valid_date(value: Any) -> bool:
    if not filled(value):
        return False
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed <= datetime.now(timezone.utc)
    except ValueError:
        return False


def approval_issues(document: MarkdownDocument) -> list[str]:
    record = document.metadata.get("approval")
    status = document.metadata.get("document", {}).get("status")
    issues = []
    if status not in {"approved", "released", "已批准", "已发布"}:
        issues.append("document.status is not approved/released")
    if not isinstance(record, dict):
        return issues + ["approval record is missing; machine review is not human approval"]
    if not filled(record.get("reviewer")):
        issues.append("approval.reviewer is missing")
    if not valid_date(record.get("approved_at")):
        issues.append("approval.approved_at is missing/invalid/future")
    if record.get("content_sha256") != fingerprint(document):
        issues.append("approval fingerprint does not match the current content")
    return issues


def tailoring_minimum(document: MarkdownDocument, kind: str, floor: int) -> tuple[int, list[str]]:
    decisions = [a for a in document.artifacts_of("tailoring") if a.data.get("target_kind") == kind]
    if not decisions:
        return floor, []
    if len(decisions) != 1:
        return floor, [f"multiple tailoring decisions for {kind}"]
    record = decisions[0].data
    required = ("id", "rationale", "impact", "source_refs", "approved_by", "approved_at")
    if (record.get("status") != "approved" or not all(filled(record.get(k)) for k in required)
            or not valid_date(record.get("approved_at"))):
        return floor, [f"tailoring for {kind} is not explicitly approved and complete"]
    value = record.get("accepted_minimum")
    if (isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= floor
            or record.get("required_minimum") != floor):
        return floor, [f"tailoring for {kind} has invalid/originally mismatched minimum"]
    source_ids = {s.get("id") for s in document.metadata.get("sources", []) if isinstance(s, dict)}
    refs = record["source_refs"]
    if not isinstance(refs, list) or any(str(x).split("#", 1)[0] not in source_ids for x in refs):
        return floor, [f"tailoring for {kind} references an unknown source"]
    return value, []
