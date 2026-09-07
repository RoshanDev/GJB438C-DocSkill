from pathlib import Path

import pytest
import yaml

from gjb438c_suite.cli import build_parser, main
from gjb438c_suite.profile_quality import (
    audit_markdown_with_profile,
    load_profile_mapping,
    tier_minimum,
)
from gjb438c_suite.profiles import load_profile
from gjb438c_suite.registry import iter_document_types
from gjb438c_suite.suite import initialize_suite
from gjb438c_suite.volume import VolumeError, minimum_body_pages


CODES = [item.code for item in iter_document_types()]


def test_cli_exposes_real_profile_volume_and_suite_commands():
    parser = build_parser()
    for argv in (
        ["profile", "--type", "SRS"],
        ["volume-policy", "--type", "SDD", "--scale", "large"],
        ["suite-init", "--output", "out"],
        ["audit-volume", "x.docx", "--source", "x.md"],
        ["audit-suite", "suite.yaml"],
    ):
        parser.parse_args(argv)


def test_all_20_profiles_are_loadable_and_isolated():
    assert len(CODES) == 20
    for code in CODES:
        first = load_profile(code)
        second = load_profile(code)
        assert first is not second
        mapping = load_profile_mapping(code)
        assert mapping["code"] == code
        assert mapping["outline"]
        assert mapping["artifact_contracts"]


def test_tier_specific_minimum_is_not_collapsed_to_one():
    mapping = load_profile_mapping("SRS")
    requirement = next(item for item in mapping["artifact_contracts"] if item["kind"] == "requirement")
    assert tier_minimum(requirement["minimum"], "large") == int(requirement["minimum"]["large"])
    assert tier_minimum(requirement["minimum"], "large") > 1


def test_init_works_without_repository_template_root(tmp_path: Path):
    project = Path(__file__).resolve().parents[1] / "examples/project.yaml"
    for code in CODES:
        target = tmp_path / f"{code}.md"
        assert main(["init", "--type", code, "--project", str(project), "--output", str(target)]) == 0
        raw = target.read_text(encoding="utf-8")
        assert raw.startswith("---")
        assert code in raw


def test_suite_init_creates_native_unicode_20_document_workspace(tmp_path: Path):
    project = Path(__file__).resolve().parents[1] / "examples/project.yaml"
    manifest = initialize_suite(
        tmp_path / "suite",
        project=project,
        tier="large",
        min_body_pages=300,
        suite_id="PUBLIC-DEMO",
    )
    payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    assert len(payload["documents"]) == 20
    assert set(payload["documents"]) == set(CODES)
    for code, entry in payload["documents"].items():
        path = manifest.parent / entry["markdown"]
        assert path.is_file()
        assert "#U" not in path.name
        metadata = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
        assert metadata["document"]["type"] == code
        assert metadata["document"]["status"] == "draft"
        assert metadata["quality"]["min_body_pages"] >= 300


def test_page_override_can_raise_but_not_lower_profile_floor():
    floor = minimum_body_pages("SSS", "large")
    with pytest.raises(VolumeError):
        minimum_body_pages("SSS", "large", floor - 1)
    assert minimum_body_pages("SSS", "large", floor + 50) == floor + 50


def test_zcode_style_plain_markdown_is_rejected(tmp_path: Path):
    source = tmp_path / "SSS.md"
    source.write_text("# 修订说明\n\n# 1 范围\n\n这只是普通摘要，没有元数据和结构化证据。\n", encoding="utf-8")
    report = audit_markdown_with_profile(
        source,
        profile="release",
        document_type="SSS",
        tier="large",
    )
    assert not report.passed
    text = report.to_text()
    assert "ERROR" in text
    assert "gjb-requirement" in text or "元数据" in text or "front" in text.lower()
