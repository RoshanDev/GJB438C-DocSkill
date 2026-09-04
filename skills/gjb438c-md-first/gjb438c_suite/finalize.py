from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


class FinalizeError(RuntimeError):
    pass


def _find_libreoffice() -> str:
    executable = shutil.which("libreoffice") or shutil.which("soffice")
    if not executable:
        raise FinalizeError("未找到 LibreOffice/soffice；请在 Word/WPS 中全选并按 F9 更新目录")
    return executable


def _uno_pythonpath() -> str | None:
    candidates = [
        Path("/usr/lib/python3/dist-packages"),
        Path("/usr/lib/libreoffice/program"),
    ]
    existing = [str(path) for path in candidates if path.exists()]
    return os.pathsep.join(existing) if existing else None


def _write_uno_updater(path: Path) -> None:
    path.write_text(
        r'''from pathlib import Path
import sys
import uno


def prop(name, value):
    item = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
    item.Name = name
    item.Value = value
    return item

source = Path(sys.argv[1]).resolve()
context = uno.getComponentContext()
resolver = context.ServiceManager.createInstanceWithContext(
    "com.sun.star.bridge.UnoUrlResolver", context
)
remote = resolver.resolve(
    "uno:socket,host=127.0.0.1,port=20863;urp;StarOffice.ComponentContext"
)
desktop = remote.ServiceManager.createInstanceWithContext(
    "com.sun.star.frame.Desktop", remote
)
document = desktop.loadComponentFromURL(
    uno.systemPathToFileUrl(str(source)),
    "_blank",
    0,
    (prop("Hidden", True), prop("ReadOnly", False)),
)
if document is None:
    raise RuntimeError(f"LibreOffice 无法打开 {source}")
try:
    indexes = document.getDocumentIndexes()
    for index in range(indexes.getCount()):
        indexes.getByIndex(index).update()
    document.getTextFields().refresh()
    document.store()
finally:
    document.close(True)
''',
        encoding="utf-8",
    )


def _run_libreoffice_update(source: Path, destination: Path) -> None:
    office = _find_libreoffice()
    shutil.copy2(source, destination)
    with tempfile.TemporaryDirectory(prefix="gjb438c-lo-") as temp_name:
        temp = Path(temp_name)
        profile = temp / "profile"
        home = temp / "home"
        profile.mkdir()
        home.mkdir()
        updater = temp / "update.py"
        _write_uno_updater(updater)
        env = os.environ.copy()
        env["HOME"] = str(home)
        env.setdefault("TERM", "xterm")
        pythonpath = _uno_pythonpath()
        if pythonpath:
            env["PYTHONPATH"] = pythonpath + (
                os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
            )
        server = subprocess.Popen(
            [
                office,
                f"-env:UserInstallation={profile.resolve().as_uri()}",
                "--headless",
                "--nologo",
                "--nodefault",
                "--nofirststartwizard",
                "--accept=socket,host=127.0.0.1,port=20863;urp;StarOffice.ServiceManager",
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            last_error: Exception | None = None
            for _ in range(20):
                result = subprocess.run(
                    [sys.executable, str(updater), str(destination)],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                if result.returncode == 0:
                    return
                last_error = FinalizeError(result.stderr.strip() or result.stdout.strip())
                time.sleep(0.35)
            raise FinalizeError(f"LibreOffice 更新目录失败：{last_error}")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()


def _toc_element(root: etree._Element) -> etree._Element:
    body = root.find("./w:body", NS)
    if body is None:
        raise FinalizeError("DOCX 缺少 document body")
    for element in body:
        instructions = " ".join(element.xpath(".//w:instrText/text()", namespaces=NS))
        if "TOC" in instructions:
            return element
    raise FinalizeError("未找到 Word TOC 域")


def _strip_section_properties(element: etree._Element) -> None:
    terminal_paragraphs: list[etree._Element] = []
    for sect_pr in element.xpath(".//w:sectPr", namespaces=NS):
        paragraph = sect_pr.getparent().getparent() if sect_pr.getparent() is not None else None
        parent = sect_pr.getparent()
        if parent is not None:
            parent.remove(sect_pr)
        if paragraph is not None and paragraph.tag == f"{{{W}}}p":
            terminal_paragraphs.append(paragraph)
    # LibreOffice moves the following section break into a final empty paragraph
    # inside the TOC SDT. The original generated document already owns the correct
    # section-break paragraph, so remove this empty donor artifact as well.
    for paragraph in terminal_paragraphs:
        has_text = bool(paragraph.xpath(".//w:t[normalize-space(text())]", namespaces=NS))
        has_field = bool(paragraph.xpath(".//w:instrText", namespaces=NS))
        if not has_text and not has_field and paragraph.getparent() is not None:
            paragraph.getparent().remove(paragraph)


def _normalized_text(element: etree._Element) -> str:
    return " ".join("".join(element.xpath(".//w:t/text()", namespaces=NS)).split())


def _toc_heading_targets(donor_root: etree._Element, donor_toc: etree._Element) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    seen: set[str] = set()
    for anchor in donor_toc.xpath(".//w:hyperlink/@w:anchor", namespaces=NS):
        if anchor in seen:
            continue
        seen.add(anchor)
        bookmark = donor_root.xpath(
            './/w:bookmarkStart[@w:name=$name]', namespaces=NS, name=anchor
        )
        if len(bookmark) != 1:
            raise FinalizeError(f"LibreOffice TOC 链接 {anchor} 没有唯一标题书签")
        paragraph = bookmark[0].xpath("ancestor::w:p[1]", namespaces=NS)
        if not paragraph:
            raise FinalizeError(f"LibreOffice TOC 书签 {anchor} 不在标题段落中")
        title = _normalized_text(paragraph[0])
        if not title:
            raise FinalizeError(f"LibreOffice TOC 书签 {anchor} 的标题为空")
        targets.append((anchor, title))
    return targets


def _transplant_heading_bookmarks(
    original_root: etree._Element,
    targets: list[tuple[str, str]],
) -> None:
    body = original_root.find("./w:body", NS)
    if body is None:
        raise FinalizeError("原 DOCX 缺少 document body")
    paragraphs = body.findall("./w:p", NS)
    existing_names = set(original_root.xpath(".//w:bookmarkStart/@w:name", namespaces=NS))
    numeric_ids = []
    for value in original_root.xpath(".//w:bookmarkStart/@w:id", namespaces=NS):
        try:
            numeric_ids.append(int(value))
        except (TypeError, ValueError):
            continue
    next_id = max(numeric_ids, default=900) + 1
    cursor = 0
    for name, title in targets:
        if name in existing_names:
            continue
        match_index: int | None = None
        for index in range(cursor, len(paragraphs)):
            if _normalized_text(paragraphs[index]) == title:
                match_index = index
                break
        if match_index is None:
            # Duplicate headings or renderer-specific ordering can make the monotonic
            # search miss. A global exact-text fallback is still deterministic when
            # it yields one paragraph.
            candidates = [
                index for index, paragraph in enumerate(paragraphs)
                if _normalized_text(paragraph) == title
            ]
            if len(candidates) == 1:
                match_index = candidates[0]
        if match_index is None:
            raise FinalizeError(f"原 DOCX 中找不到 TOC 标题段落：{title}")
        paragraph = paragraphs[match_index]
        start = etree.Element(f"{{{W}}}bookmarkStart")
        start.set(f"{{{W}}}id", str(next_id))
        start.set(f"{{{W}}}name", name)
        end = etree.Element(f"{{{W}}}bookmarkEnd")
        end.set(f"{{{W}}}id", str(next_id))
        insert_at = 1 if len(paragraph) and paragraph[0].tag == f"{{{W}}}pPr" else 0
        paragraph.insert(insert_at, start)
        paragraph.append(end)
        existing_names.add(name)
        next_id += 1
        cursor = match_index + 1


def _copy_toc_cache(original: Path, donor: Path, output: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="gjb438c-toc-cache-") as temp_name:
        temp = Path(temp_name)
        original_dir = temp / "original"
        donor_dir = temp / "donor"
        original_dir.mkdir()
        donor_dir.mkdir()
        with ZipFile(original) as archive:
            archive.extractall(original_dir)
        with ZipFile(donor) as archive:
            archive.extractall(donor_dir)

        original_xml = original_dir / "word" / "document.xml"
        donor_xml = donor_dir / "word" / "document.xml"
        original_tree = etree.parse(str(original_xml))
        donor_tree = etree.parse(str(donor_xml))
        original_root = original_tree.getroot()
        donor_root = donor_tree.getroot()
        original_toc = _toc_element(original_root)
        donor_toc_source = _toc_element(donor_root)
        targets = _toc_heading_targets(donor_root, donor_toc_source)
        donor_toc = deepcopy(donor_toc_source)
        _strip_section_properties(donor_toc)
        _transplant_heading_bookmarks(original_root, targets)
        original_toc.getparent().replace(original_toc, donor_toc)
        original_tree.write(
            str(original_xml), xml_declaration=True, encoding="UTF-8", standalone="yes"
        )

        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, "w", ZIP_DEFLATED) as archive:
            for file in original_dir.rglob("*"):
                if file.is_file():
                    archive.write(file, file.relative_to(original_dir).as_posix())


def refresh_toc_cache(
    input_docx: str | Path,
    output_docx: str | Path | None = None,
) -> Path:
    """Refresh TOC with LibreOffice, but transplant only its cached TOC.

    LibreOffice can rewrite section breaks and custom styles on save. Therefore the
    updated file is used only as a donor for the TOC field result; all other OOXML
    parts remain byte-for-byte from the original generated DOCX.
    """
    source = Path(input_docx).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = Path(output_docx).resolve() if output_docx else source
    with tempfile.TemporaryDirectory(prefix="gjb438c-toc-donor-") as temp_name:
        donor = Path(temp_name) / source.name
        _run_libreoffice_update(source, donor)
        target = destination if destination != source else source.with_suffix(".finalized.docx")
        _copy_toc_cache(source, donor, target)
        if destination == source:
            target.replace(source)
            return source
        return target
