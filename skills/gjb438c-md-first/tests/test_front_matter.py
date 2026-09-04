from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from gjb438c_suite.front_matter import audit_front_matter, render_front_matter

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def test_render_front_matter(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    template = root / "templates/front-matter/standard-front-matter.docx"
    payload = json.loads(
        (root / "examples/front-matter.example.json").read_text(encoding="utf-8")
    )
    output = tmp_path / "front-matter.docx"
    render_front_matter(template, payload, output, release=True)
    report = audit_front_matter(output)
    assert report["ok"], report

    with ZipFile(output) as archive:
        document = etree.fromstring(archive.read("word/document.xml"))
    text = "".join(document.xpath(".//w:t/text()", namespaces=NS))
    assert "示例任务管理软件" in text
    assert "软件需求规格说明" in text
    assert "DEMO-2026-001" in text
    assert "建立 GJB 438C-2021 SRS 初稿" in text
    assert "XXXXXX" not in text
    assert "软件部署手册" not in text
