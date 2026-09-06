"""Typed, dependency-scoped references and coverage for document contracts.

required_any selects the first successful baseline in the profile's declared
order, matching standalone validation. Optional references do not silently add
extra coverage obligations or let an unrelated document satisfy a required one.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .markdown_doc import MarkdownDocument
from .profile_quality import artifact_kind, artifact_mapping, load_profile_mapping
from .registry import get_document_type


def selected_dependencies(code: str, available: Mapping[str, Any]) -> list[str]:
    spec = load_profile_mapping(code).get("baselines", {})
    selected = [get_document_type(str(x)).code for x in spec.get("required", [])]
    choices = [get_document_type(str(x)).code for x in spec.get("required_any", [])]
    choice = next((x for x in choices if x in available), None)
    if choice is not None:
        selected.append(choice)
    return list(dict.fromkeys(selected))


def _values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [x for x in re.split(r"[,;；\s]+", value.strip()) if x]
    if isinstance(value, (list, tuple, set)):
        return [ref for x in value for ref in _values(x)]
    return [str(value)]


def reference_issues(
    code: str,
    document: MarkdownDocument,
    baselines: Mapping[str, MarkdownDocument],
    *,
    severity: str = "ERROR",
) -> list[dict[str, str]]:
    """Only successful, selected documents may supply baseline targets.

    Coverage is checked per contract and target kind. Repeatedly referencing one
    valid ID is not coverage of the remaining baseline. Undeclared artifact kinds
    in a different document cannot populate the allowed-ID set.
    """
    issues: list[dict[str, str]] = []
    index: dict[str, set[str]] = {}
    selected = selected_dependencies(code, baselines)
    for baseline_code in selected:
        baseline = baselines.get(baseline_code)
        if baseline is None:
            continue  # Missing dependencies are reported by the baseline gate.
        declared = {c["kind"] for c in load_profile_mapping(baseline_code)["artifact_contracts"]}
        for artifact in baseline.artifacts:
            kind = artifact_kind(artifact)
            identifier = str(artifact_mapping(artifact).get("id", "")).strip()
            if kind in declared and identifier:
                index.setdefault(kind, set()).add(identifier)

    for contract in load_profile_mapping(code)["artifact_contracts"]:
        references = contract.get("references", {})
        if not isinstance(references, dict):
            continue
        targets = {name: target.split(":", 1)[1].strip()
                   for name, target in references.items()
                   if isinstance(target, str) and target.startswith("baseline:")}
        covered: dict[str, set[str]] = {kind: set() for kind in targets.values()}
        for artifact in document.artifacts_of(contract["kind"]):
            payload = artifact_mapping(artifact)
            identifier = str(payload.get("id") or "<no ID>")
            for name, target_kind in targets.items():
                allowed = index.get(target_kind, set())
                for reference in _values(payload.get(name)):
                    if reference not in allowed:
                        issues.append({"severity": severity, "code": "SUITE_REFERENCE_UNRESOLVED",
                                       "message": f"{identifier}.{name}: {reference} is not a {target_kind} in selected baselines {selected}"})
                    else:
                        covered[target_kind].add(reference)
        if contract.get("coverage") is True:
            for kind in set(targets.values()):
                missing = index.get(kind, set()) - covered[kind]
                if missing:
                    issues.append({"severity": severity, "code": "SUITE_BASELINE_COVERAGE_INCOMPLETE",
                                   "message": f"{code}/{contract['kind']} leaves {len(missing)} {kind} IDs uncovered in {selected}: "
                                              + ", ".join(sorted(missing))})
    return issues
