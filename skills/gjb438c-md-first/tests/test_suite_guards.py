from pathlib import Path

import pytest
import yaml

from gjb438c_suite.suite import SuiteError, audit_suite_manifest, initialize_suite


def test_suite_init_refuses_nonempty_directory(tmp_path: Path):
    target = tmp_path / "suite"
    target.mkdir()
    (target / "keep.txt").write_text("do not overwrite", encoding="utf-8")
    with pytest.raises(SuiteError):
        initialize_suite(target)
    assert (target / "keep.txt").read_text(encoding="utf-8") == "do not overwrite"


def test_suite_audit_reports_lowered_document_floor(tmp_path: Path):
    manifest = initialize_suite(tmp_path / "suite", tier="large")
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data["documents"]["SSS"]["min_body_pages"] = 1
    manifest.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    report = audit_suite_manifest(manifest, audit_profile="review")
    assert not report.passed
    assert any(item.code == "SUITE_PAGE_OVERRIDE_INVALID" for item in report.issues)
