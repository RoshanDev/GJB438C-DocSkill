from __future__ import annotations

from pathlib import Path

from gjb438c_suite.quality import audit_markdown
from gjb438c_suite.registry import DOCUMENT_TYPES, get_document_type, iter_document_types


def test_all_twenty_document_types_are_registered() -> None:
    items = list(iter_document_types())
    assert len(items) == 20
    assert [item.number for item in items] == list(range(1, 21))
    assert set(DOCUMENT_TYPES) == {
        "SDP", "SIP", "STrP", "STP", "OCD", "SSS", "IRS", "SSDD", "IDD", "SRS",
        "SDD", "DBDD", "STD", "STR", "SPS", "SVD", "SUM", "CPM", "FSM", "SDSR",
    }
    assert get_document_type("软件需求规格说明书").code == "SRS"
    assert get_document_type("概要设计").code == "SDD"


def test_release_examples_pass_content_gates() -> None:
    root = Path(__file__).resolve().parents[1]
    srs = root / "examples/SRS.example.md"
    sdd = root / "examples/SDD.example.md"

    srs_report = audit_markdown(srs, profile="release")
    assert srs_report.passed, srs_report.to_text()
    assert srs_report.metrics["requirements"] == 2

    sdd_report = audit_markdown(sdd, profile="release", baseline_srs=srs)
    assert sdd_report.passed, sdd_report.to_text()
    assert sdd_report.metrics["requirement_coverage_percent"] == 100.0
    assert sdd_report.metrics["design_units"] >= 2


def test_sdd_unknown_internal_reference_is_blocked(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    srs = root / "examples/SRS.example.md"
    original = (root / "examples/SDD.example.md").read_text(encoding="utf-8")
    broken = original.replace(
        "interfaces: [IF-TASK-API, IF-TASK-EVENT]",
        "interfaces: [IF-TASK-API, IF-NOT-FOUND]",
        1,
    )
    path = tmp_path / "SDD.broken.md"
    path.write_text(broken, encoding="utf-8")
    report = audit_markdown(path, profile="release", baseline_srs=srs)
    assert not report.passed
    assert any(issue.code == "REFERENCE_UNKNOWN" for issue in report.errors)


def test_srs_untraced_requirement_is_blocked(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    original = (root / "examples/SRS.example.md").read_text(encoding="utf-8")
    broken = original.replace(
        "requirements: [REQ-TASK-001, REQ-ACCESS-001]",
        "requirements: [REQ-TASK-001]",
        1,
    )
    path = tmp_path / "SRS.broken.md"
    path.write_text(broken, encoding="utf-8")
    report = audit_markdown(path, profile="release")
    assert not report.passed
    assert any(issue.code == "SRS_REQUIREMENT_UNTRACED" for issue in report.errors)
