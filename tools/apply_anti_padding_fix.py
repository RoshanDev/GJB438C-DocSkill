from __future__ import annotations

from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/gjb438c-md-first"
PKG = SKILL / "gjb438c_suite"
TESTS = SKILL / "tests"

policy_path = PKG / "data/volume-policy.yaml"
policy = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
policy["minimum_visible_chars_per_page"] = {
    "prototype": 0,
    "small": 140,
    "medium": 160,
    "large": 180,
    "very-large": 200,
}
policy["maximum_duplicate_prose_ratio"] = {
    "prototype": 1.0,
    "small": 0.12,
    "medium": 0.10,
    "large": 0.08,
    "very-large": 0.06,
}
policy["minimum_duplicate_paragraph_chars"] = 80
policy_path.write_text(
    yaml.safe_dump(policy, allow_unicode=True, sort_keys=False), encoding="utf-8"
)

volume_path = PKG / "volume.py"
text = volume_path.read_text(encoding="utf-8")

old_fields = '''    minimum_effective_units: int
    passed: bool
    issues: tuple[str, ...]
    policy_version: int
    source_sha256: str
    docx_sha256: str
'''
new_fields = '''    minimum_effective_units: int
    minimum_visible_chars: int
    duplicate_chars: int
    duplicate_ratio: float
    max_paragraph_repeat: int
    passed: bool
    issues: tuple[str, ...]
    policy_version: int
    source_sha256: str
    docx_sha256: str
'''
if old_fields not in text:
    raise SystemExit("VolumeResult fields block not found")
text = text.replace(old_fields, new_fields)

old_dict = '''            "minimum_effective_units": self.minimum_effective_units,
            "passed": self.passed,
            "issues": list(self.issues),
'''
new_dict = '''            "minimum_effective_units": self.minimum_effective_units,
            "minimum_visible_chars": self.minimum_visible_chars,
            "duplicate_chars": self.duplicate_chars,
            "duplicate_ratio": self.duplicate_ratio,
            "max_paragraph_repeat": self.max_paragraph_repeat,
            "passed": self.passed,
            "issues": list(self.issues),
'''
if old_dict not in text:
    raise SystemExit("VolumeResult as_dict block not found")
text = text.replace(old_dict, new_dict)

old_text = '''            f"pages={self.pages}/{self.minimum_pages} "
            f"effective_units={self.effective_units}/{self.minimum_effective_units}{tail}"
'''
new_text = '''            f"pages={self.pages}/{self.minimum_pages} "
            f"visible_chars={self.visible_chars}/{self.minimum_visible_chars} "
            f"effective_units={self.effective_units}/{self.minimum_effective_units} "
            f"duplicate_ratio={self.duplicate_ratio:.2%}{tail}"
'''
if old_text not in text:
    raise SystemExit("VolumeResult to_text block not found")
text = text.replace(old_text, new_text)

old_effective = '''def effective_units(document: MarkdownDocument) -> tuple[int, int]:
    chars = _visible_chars(document)
    units = (
        chars
        + _table_count(document) * 700
        + _figure_count(document) * 550
        + len(document.artifacts) * 180
    )
    return chars, units
'''
new_effective = r'''def _normalized_prose_paragraphs(document: MarkdownDocument) -> list[str]:
    policy = load_volume_policy()
    minimum = int(policy.get("minimum_duplicate_paragraph_chars", 80))
    body = strip_quality_blocks(document.body)
    body = re.sub(r"!\[[^]]*\]\([^)]*\)", "", body)
    result: list[str] = []
    for block in re.split(r"\n\s*\n+", body):
        lines = []
        for line in block.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^\|(?:\s*:?-{3,}:?\s*\|)+$", stripped):
                continue
            lines.append(stripped)
        normalized = re.sub(r"[\s\W_]+", "", "".join(lines), flags=re.UNICODE)
        if len(normalized) >= minimum:
            result.append(normalized)
    return result


def duplicate_content_metrics(document: MarkdownDocument) -> tuple[int, float, int]:
    paragraphs = _normalized_prose_paragraphs(document)
    if not paragraphs:
        return 0, 0.0, 0
    counts = Counter(paragraphs)
    total_chars = sum(len(value) for value in paragraphs)
    duplicate_chars = sum((count - 1) * len(value) for value, count in counts.items())
    ratio = duplicate_chars / total_chars if total_chars else 0.0
    return duplicate_chars, ratio, max(counts.values(), default=0)


def effective_units(document: MarkdownDocument) -> tuple[int, int]:
    chars = _visible_chars(document)
    duplicate_chars, _, _ = duplicate_content_metrics(document)
    deduplicated_chars = max(0, chars - duplicate_chars)
    units = (
        deduplicated_chars
        + _table_count(document) * 700
        + _figure_count(document) * 550
        + len(document.artifacts) * 180
    )
    return chars, units
'''
if old_effective not in text:
    raise SystemExit("effective_units block not found")
text = text.replace(old_effective, new_effective)

old_preflight = '''    pages = minimum_pages(profile.document_type.code, scale)
    _, units = effective_units(document)
    floor = pages * int(policy.get("text_equivalent_chars_per_page", 260))
    if units < floor:
'''
new_preflight = '''    pages = minimum_pages(profile.document_type.code, scale)
    visible_chars, units = effective_units(document)
    floor = pages * int(policy.get("text_equivalent_chars_per_page", 260))
    visible_floor = pages * int(policy["minimum_visible_chars_per_page"][scale])
    duplicate_chars, duplicate_ratio, max_repeat = duplicate_content_metrics(document)
    if visible_chars < visible_floor:
        issues.append(
            {
                "severity": severity,
                "code": "VOLUME_VISIBLE_CONTENT_TOO_THIN",
                "message": (
                    f"可见正文字符 {visible_chars} 低于 {profile.document_type.code}/{scale} "
                    f"最低值 {visible_floor}；隐藏证据块和空白页不能替代交付正文"
                ),
            }
        )
    duplicate_limit = float(policy["maximum_duplicate_prose_ratio"][scale])
    if max_repeat >= 3 and duplicate_ratio > duplicate_limit:
        issues.append(
            {
                "severity": severity,
                "code": "VOLUME_DUPLICATE_CONTENT",
                "message": (
                    f"重复长段落占比 {duplicate_ratio:.2%} 超过 {duplicate_limit:.2%}，"
                    f"最大重复次数 {max_repeat}；重复内容不计入有效体量"
                ),
            }
        )
    if units < floor:
'''
if old_preflight not in text:
    raise SystemExit("markdown preflight block not found")
text = text.replace(old_preflight, new_preflight)

old_rendered = '''    chars, units = effective_units(document)
    policy = load_volume_policy()
    unit_floor = floor * int(policy.get("text_equivalent_chars_per_page", 260))
    issues: list[str] = []
    if pages < floor:
        issues.append(
            f"渲染页数 {pages} 低于 {profile.document_type.code}/{scale} 发布下限 {floor}"
        )
    if units < unit_floor:
        issues.append(f"等效内容单位 {units} 低于反灌水下限 {unit_floor}")
    return VolumeResult(
        profile.document_type.code,
        scale,
        pages,
        floor,
        chars,
        units,
        unit_floor,
        not issues,
        tuple(issues),
        int(policy.get("policy_version", 1)),
        sha256_text(document.raw),
        sha256_file(docx_path),
    )
'''
new_rendered = '''    chars, units = effective_units(document)
    policy = load_volume_policy()
    unit_floor = floor * int(policy.get("text_equivalent_chars_per_page", 260))
    visible_floor = pages * int(policy["minimum_visible_chars_per_page"][scale])
    duplicate_chars, duplicate_ratio, max_repeat = duplicate_content_metrics(document)
    duplicate_limit = float(policy["maximum_duplicate_prose_ratio"][scale])
    issues: list[str] = []
    if pages < floor:
        issues.append(
            f"渲染页数 {pages} 低于 {profile.document_type.code}/{scale} 发布下限 {floor}"
        )
    if chars < visible_floor:
        issues.append(
            f"按实际 {pages} 页计算，可见正文字符 {chars} 低于最低值 {visible_floor}"
        )
    if max_repeat >= 3 and duplicate_ratio > duplicate_limit:
        issues.append(
            f"重复长段落占比 {duplicate_ratio:.2%} 超过 {duplicate_limit:.2%}，最大重复次数 {max_repeat}"
        )
    if units < unit_floor:
        issues.append(f"去重后的等效内容单位 {units} 低于反灌水下限 {unit_floor}")
    return VolumeResult(
        profile.document_type.code,
        scale,
        pages,
        floor,
        chars,
        units,
        unit_floor,
        visible_floor,
        duplicate_chars,
        round(duplicate_ratio, 6),
        max_repeat,
        not issues,
        tuple(issues),
        int(policy.get("policy_version", 1)),
        sha256_text(document.raw),
        sha256_file(docx_path),
    )
'''
if old_rendered not in text:
    raise SystemExit("audit_rendered_volume block not found")
text = text.replace(old_rendered, new_rendered)
volume_path.write_text(text, encoding="utf-8")

(TESTS / "test_duplicate_content_gate.py").write_text(r'''from pathlib import Path

from gjb438c_suite.markdown_doc import parse_markdown
from gjb438c_suite.profiles import load_profile
from gjb438c_suite.volume import (
    duplicate_content_metrics,
    effective_units,
    markdown_volume_issues,
)


def test_repeated_long_paragraph_is_penalized_and_blocked(tmp_path: Path):
    source = Path(__file__).resolve().parents[1] / "examples/SRS.example.md"
    raw = source.read_text(encoding="utf-8")
    repeated = (
        "本段仅用于验证反注水门禁。它包含足够长度的技术文字，但被机械重复时不应增加有效体量。"
        "真实文档必须给出项目特定条件、输入、处理、输出、异常、验证方法和来源证据。"
    )
    target = tmp_path / "repeated.md"
    target.write_text(raw + "\n\n" + "\n\n".join([repeated] * 12), encoding="utf-8")
    document = parse_markdown(target)
    duplicate_chars, ratio, max_repeat = duplicate_content_metrics(document)
    assert duplicate_chars > 0
    assert ratio > 0.5
    assert max_repeat == 12
    visible, units = effective_units(document)
    assert units < visible + len(document.artifacts) * 180 + 10000
    issues = markdown_volume_issues(
        document,
        load_profile("SRS"),
        "large",
        "release",
        True,
    )
    assert any(issue["code"] == "VOLUME_DUPLICATE_CONTENT" for issue in issues)


def test_distinct_long_paragraphs_are_not_marked_duplicate(tmp_path: Path):
    source = Path(__file__).resolve().parents[1] / "examples/SRS.example.md"
    raw = source.read_text(encoding="utf-8")
    paragraphs = [
        ("第%d段描述不同的工程条件、数据来源、处理约束、异常路径和验证结果。" % index)
        + ("该内容不能与其他段完全相同。" * 8)
        for index in range(12)
    ]
    target = tmp_path / "distinct.md"
    target.write_text(raw + "\n\n" + "\n\n".join(paragraphs), encoding="utf-8")
    duplicate_chars, ratio, max_repeat = duplicate_content_metrics(parse_markdown(target))
    assert duplicate_chars == 0
    assert ratio == 0
    assert max_repeat <= 1
''', encoding="utf-8")

for rel in (
    "README.md",
    "docs/VOLUME-POLICY.md",
    "docs/PAGE-COUNT-RESEARCH.md",
    "skills/gjb438c-md-first/README.md",
    "skills/gjb438c-md-first/SKILL.md",
):
    path = ROOT / rel
    raw = path.read_text(encoding="utf-8")
    if "重复长段落占比" not in raw:
        raw += '''

## 反注水补充

发布门禁同时检查按实际渲染页数计算的可见正文字符密度，并对长度达到阈值的完全重复段落去重。重复长段落占比超过项目规模上限时直接失败；被判定为重复的字符不会计入等效内容单位。结构化证据块也不能代替最终 Word 中可见的技术正文。
'''
        path.write_text(raw, encoding="utf-8")

Path(__file__).unlink()
print("anti-padding duplicate-content gates applied")
