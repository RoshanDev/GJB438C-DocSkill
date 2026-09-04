from __future__ import annotations

from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/gjb438c-md-first"
PKG = SKILL / "gjb438c_suite"
TESTS = SKILL / "tests"

# 1. A caller may raise a page floor, but must never lower the repository policy.
volume_path = PKG / "volume.py"
text = volume_path.read_text(encoding="utf-8")
old = '''def minimum_pages(document_type: str, scale: str, override: int | None = None) -> int:
    if override is not None:
        return max(0, int(override))
    try:
        return int(load_volume_policy()["documents"][document_type.upper()][scale])
    except KeyError as exc:
        raise VolumeError(f"缺少 {document_type}/{scale} 页数策略") from exc
'''
new = '''def minimum_pages(document_type: str, scale: str, override: int | None = None) -> int:
    try:
        policy_floor = int(load_volume_policy()["documents"][document_type.upper()][scale])
    except KeyError as exc:
        raise VolumeError(f"缺少 {document_type}/{scale} 页数策略") from exc
    if override is None:
        return policy_floor
    requested = int(override)
    if requested < policy_floor:
        raise VolumeError(
            f"--min-pages/manifest min_pages 只能提高下限；"
            f"{document_type.upper()}/{scale} 策略下限为 {policy_floor}，不能降为 {requested}"
        )
    return requested
'''
if old not in text:
    raise SystemExit("volume.py minimum_pages block not found")
text = text.replace(old, new)

needle = '''    policy = load_volume_policy()
    severity = "ERROR" if audit_profile == "release" else "WARN"
    issues: list[dict[str, Any]] = []
    if audit_profile == "release" and not scale_declared:
'''
replacement = '''    policy = load_volume_policy()
    severity = "ERROR" if audit_profile == "release" else "WARN"
    issues: list[dict[str, Any]] = []
    quality = document.metadata.get("quality")
    fixture = isinstance(quality, dict) and quality.get("fixture") is True
    if audit_profile == "release" and scale == "prototype" and not fixture:
        issues.append(
            {
                "severity": "ERROR",
                "code": "VOLUME_PROTOTYPE_RELEASE_FORBIDDEN",
                "message": (
                    "prototype 仅供仓库示例和 CI 夹具；生产发布必须选择 small、medium、large "
                    "或 very-large。确属测试夹具时需显式设置 quality.fixture: true"
                ),
            }
        )
    if audit_profile == "release" and not scale_declared:
'''
if needle not in text:
    raise SystemExit("volume.py markdown_volume_issues insertion point not found")
text = text.replace(needle, replacement)
volume_path.write_text(text, encoding="utf-8")

# 2. Suite floors are derived from the selected document set and are raise-only.
suite_path = PKG / "suite.py"
text = suite_path.read_text(encoding="utf-8")
if "import math\n" not in text:
    text = text.replace("import json\n", "import json\nimport math\n")
text = text.replace(
    "    VALID_SCALES,\n    load_volume_policy,",
    "    VALID_SCALES,\n    VolumeError,\n    load_volume_policy,",
)
needle = '''    report = SuiteAuditReport(manifest_path, selected_scale)
    policy = load_volume_policy()
    expected_values = suite.get("required_documents")
'''
replacement = '''    report = SuiteAuditReport(manifest_path, selected_scale)
    policy = load_volume_policy()
    if selected_scale == "prototype" and suite.get("fixture") is not True:
        _add(
            report,
            "ERROR",
            "SUITE_PROTOTYPE_RELEASE_FORBIDDEN",
            "prototype 套件仅供示例/CI；生产套件必须使用 small 或更高规模",
        )
    expected_values = suite.get("required_documents")
'''
if needle not in text:
    raise SystemExit("suite.py prototype insertion point not found")
text = text.replace(needle, replacement)

old = '''        pages = int(volume.get("pages", 0))
        floor = minimum_pages(code, selected_scale, entry.get("min_pages"))
        units = int(volume.get("effective_units", 0))
'''
new = '''        pages = int(volume.get("pages", 0))
        try:
            floor = minimum_pages(code, selected_scale, entry.get("min_pages"))
        except VolumeError as exc:
            _add(report, "ERROR", "SUITE_PAGE_OVERRIDE_INVALID", str(exc), code)
            floor = minimum_pages(code, selected_scale)
        units = int(volume.get("effective_units", 0))
'''
if old not in text:
    raise SystemExit("suite.py per-document floor block not found")
text = text.replace(old, new)

old = '''    override = suite.get("min_portfolio_pages")
    report.minimum_total_pages = (
        int(override)
        if override is not None
        else int(policy["portfolio_min_pages"][selected_scale])
    )
    if report.total_pages < report.minimum_total_pages:
'''
new = '''    all_codes = [item.code for item in iter_document_types()]
    full_floor = int(policy["portfolio_min_pages"][selected_scale])
    all_individual_pages = sum(minimum_pages(code, selected_scale) for code in all_codes)
    selected_individual_pages = sum(minimum_pages(code, selected_scale) for code in expected)
    portfolio_factor = max(
        1.0,
        full_floor / all_individual_pages if all_individual_pages else 1.0,
    )
    computed_floor = (
        full_floor
        if set(expected) == set(all_codes)
        else math.ceil(selected_individual_pages * portfolio_factor)
    )
    override = suite.get("min_portfolio_pages")
    if override is not None and int(override) < computed_floor:
        _add(
            report,
            "ERROR",
            "SUITE_PORTFOLIO_OVERRIDE_INVALID",
            f"min_portfolio_pages 只能提高下限；当前裁剪集下限为 {computed_floor}，不能降为 {int(override)}",
        )
    report.minimum_total_pages = max(computed_floor, int(override or 0))
    if report.total_pages < report.minimum_total_pages:
'''
if old not in text:
    raise SystemExit("suite.py portfolio floor block not found")
text = text.replace(old, new)
suite_path.write_text(text, encoding="utf-8")

# 3. Repository examples are explicitly marked as test fixtures.
for name in ("SRS.example.md", "SDD.example.md"):
    path = SKILL / "examples" / name
    raw = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", raw, re.S)
    if not match:
        raise SystemExit(f"front matter not found: {path}")
    metadata = yaml.safe_load(match.group(1)) or {}
    quality = metadata.setdefault("quality", {})
    quality["scale"] = "prototype"
    quality["fixture"] = True
    path.write_text(
        "---\n"
        + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip()
        + "\n---\n"
        + raw[match.end():],
        encoding="utf-8",
    )

suite_example = SKILL / "examples/suite.example.yaml"
data = yaml.safe_load(suite_example.read_text(encoding="utf-8")) or {}
data.setdefault("suite", {})["fixture"] = True
suite_example.write_text(
    yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8"
)

# Existing suite test uses a prototype manifest; mark it as an explicit fixture.
test_suite = TESTS / "test_suite_audit.py"
raw = test_suite.read_text(encoding="utf-8")
raw = raw.replace(
    '"suite": {"scale": "prototype", "required_documents": ["SRS"], "min_portfolio_pages": 1},',
    '"suite": {"scale": "prototype", "fixture": True, "required_documents": ["SRS"], "min_portfolio_pages": 1},',
)
test_suite.write_text(raw, encoding="utf-8")

# 4. Regression tests for all formerly bypassable paths.
(TESTS / "test_volume_floor_integrity.py").write_text('''from pathlib import Path
import json
import shutil
import yaml
import pytest

from gjb438c_suite import suite
from gjb438c_suite.markdown_doc import parse_markdown
from gjb438c_suite.profiles import load_profile
from gjb438c_suite.volume import (
    VolumeError,
    load_volume_policy,
    markdown_volume_issues,
    minimum_pages,
    sha256_file,
    sha256_text,
)


class Passed:
    passed = True
    def to_text(self):
        return "PASS"


def test_min_pages_override_cannot_lower_policy():
    base = minimum_pages("SDD", "large")
    assert base >= 200
    with pytest.raises(VolumeError):
        minimum_pages("SDD", "large", base - 1)
    assert minimum_pages("SDD", "large", base + 10) == base + 10


def test_prototype_release_requires_explicit_fixture_marker():
    source = Path(__file__).resolve().parents[1] / "examples/SRS.example.md"
    document = parse_markdown(source)
    document.metadata["quality"] = {"scale": "prototype"}
    issues = markdown_volume_issues(
        document, load_profile("SRS"), "prototype", "release", True
    )
    assert any(issue["code"] == "VOLUME_PROTOTYPE_RELEASE_FORBIDDEN" for issue in issues)
    document.metadata["quality"]["fixture"] = True
    issues = markdown_volume_issues(
        document, load_profile("SRS"), "prototype", "release", True
    )
    assert not any(issue["code"] == "VOLUME_PROTOTYPE_RELEASE_FORBIDDEN" for issue in issues)


def _suite_fixture(tmp_path: Path, *, portfolio_floor: int, fixture: bool):
    source = Path(__file__).resolve().parents[1] / "examples/SRS.example.md"
    markdown = tmp_path / "SRS.md"
    shutil.copy2(source, markdown)
    docx = tmp_path / "SRS.docx"
    docx.write_bytes(b"synthetic-docx-for-floor-test")
    policy = load_volume_policy()
    payload = {
        "document_type": "SRS",
        "scale": "prototype",
        "pages": 3,
        "minimum_pages": 1,
        "visible_chars": 1000,
        "effective_units": 1000,
        "minimum_effective_units": 260,
        "passed": True,
        "issues": [],
        "policy_version": policy["policy_version"],
        "source_sha256": sha256_text(parse_markdown(markdown).raw),
        "docx_sha256": sha256_file(docx),
    }
    volume = tmp_path / "SRS.volume.json"
    volume.write_text(json.dumps(payload), encoding="utf-8")
    manifest = tmp_path / "suite.yaml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "suite": {
                    "scale": "prototype",
                    "fixture": fixture,
                    "required_documents": ["SRS"],
                    "min_portfolio_pages": portfolio_floor,
                },
                "documents": [
                    {
                        "type": "SRS",
                        "markdown": "SRS.md",
                        "docx": "SRS.docx",
                        "volume": "SRS.volume.json",
                    }
                ],
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return manifest


def test_suite_prototype_requires_fixture(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(suite, "audit_markdown_with_profile", lambda *a, **k: Passed())
    monkeypatch.setattr(suite, "audit_docx", lambda *a, **k: Passed())
    report = suite.audit_suite_manifest(_suite_fixture(tmp_path, portfolio_floor=1, fixture=False))
    assert any(issue.code == "SUITE_PROTOTYPE_RELEASE_FORBIDDEN" for issue in report.errors)


def test_suite_portfolio_override_cannot_lower_computed_floor(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(suite, "audit_markdown_with_profile", lambda *a, **k: Passed())
    monkeypatch.setattr(suite, "audit_docx", lambda *a, **k: Passed())
    report = suite.audit_suite_manifest(_suite_fixture(tmp_path, portfolio_floor=0, fixture=True))
    assert any(issue.code == "SUITE_PORTFOLIO_OVERRIDE_INVALID" for issue in report.errors)
''', encoding="utf-8")

# 5. Documentation makes the non-bypassable behavior explicit.
for rel in ("README.md", "docs/VOLUME-POLICY.md", "docs/PAGE-COUNT-RESEARCH.md"):
    path = ROOT / rel
    raw = path.read_text(encoding="utf-8")
    marker = "\n## 下限不可下调\n"
    if marker not in raw:
        raw += '''

## 下限不可下调

`--min-pages`、manifest 中的 `documents[].min_pages` 和 `suite.min_portfolio_pages` 只允许提高仓库策略下限，不能降低。`prototype` 仅供仓库示例与 CI 夹具，且必须显式标记 `quality.fixture: true` / `suite.fixture: true`；生产发布必须选择 `small` 或更高规模。
'''
        path.write_text(raw, encoding="utf-8")

skill_readme = SKILL / "README.md"
raw = skill_readme.read_text(encoding="utf-8")
if "下限参数只能提高" not in raw:
    raw += '''

## 生产发布限制

`prototype` 仅用于示例和 CI。生产发布使用 `small / medium / large / very-large`。页数覆盖参数只能提高策略下限，不能降低；修改 Markdown 或 DOCX 后必须重新生成体量报告。
'''
    skill_readme.write_text(raw, encoding="utf-8")

# Self-delete; workflow is removed in its final commit as well.
Path(__file__).unlink()
print("volume floor integrity fix applied")
