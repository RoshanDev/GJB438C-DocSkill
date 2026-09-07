from pathlib import Path

from gjb438c_suite.markdown_doc import parse_markdown
from gjb438c_suite.volume import duplicate_prose_metrics, markdown_volume_issues


def _source(tmp_path: Path, paragraphs: list[str]) -> Path:
    path = tmp_path / "SRS.md"
    path.write_text(
        """---
document:
  type: SRS
  id: TEST-SRS
  status: approved
quality:
  tier: large
software:
  name: 示例软件
  identifier: TEST
  version: V1.0
sources:
  - id: SRC-1
    title: 示例来源
---
# 1 范围

""" + "\n\n".join(paragraphs),
        encoding="utf-8",
    )
    return path


def test_repeated_long_prose_is_not_counted_as_real_volume(tmp_path: Path):
    repeated = (
        "本段用于验证重复内容门禁，真实文档必须给出项目特定的输入、处理、输出、异常、"
        "边界条件、来源和验证方法，机械复制同一段落不能增加有效正文体量。"
    )
    document = parse_markdown(_source(tmp_path, [repeated] * 20))
    duplicate_chars, ratio, repeat = duplicate_prose_metrics(document)
    assert duplicate_chars > 0
    assert ratio > 0.8
    assert repeat == 20
    issues = markdown_volume_issues(document, "SRS", "large", "release")
    assert any(item["code"] == "VOLUME_DUPLICATE_CONTENT" for item in issues)


def test_distinct_prose_is_not_marked_as_duplicate(tmp_path: Path):
    paragraphs = [
        f"第{index}段给出不同的条件、数据、状态、处理路径、异常恢复和验收结果。"
        + (f"唯一证据编号为 EVID-{index:03d}。" * 8)
        for index in range(20)
    ]
    document = parse_markdown(_source(tmp_path, paragraphs))
    duplicate_chars, ratio, repeat = duplicate_prose_metrics(document)
    assert duplicate_chars == 0
    assert ratio == 0
    assert repeat <= 1
