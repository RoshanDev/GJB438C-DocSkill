"""A shared, monotone main-body/back-matter boundary for authoring and volume.

Page targets are project policy for main chapters, never the entire text after
TOC. This is structural classification, not a claim to detect arbitrary prose
padding or authenticate human-written content.
"""
from dataclasses import dataclass
import re

PAGE_COUNT_SCOPE = "main_body_only_v1"
MAIN_BOOKMARK = "GJB_MAIN_BODY"
BACK_BOOKMARK = "GJB_BACK_MATTER"


def mask_comments(text: str) -> str:
    """Mask prose comments, but preserve literal comments inside code fences."""
    output, fence = [], None
    in_comment = False
    for line in text.splitlines(keepends=True):
        if fence:
            output.append(line)
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) +
                            r"{" + str(fence[1]) + r",}\s*", line):
                fence = None
            continue
        pieces, pos = [], 0
        while pos < len(line):
            if in_comment:
                close = line.find("-->", pos)
                stop = len(line) if close < 0 else close + 3
                pieces.append(re.sub(r"[^\r\n]", " ", line[pos:stop]))
                pos = stop
                if close >= 0:
                    in_comment = False
            else:
                opening = line.find("<!--", pos)
                if opening < 0:
                    pieces.append(line[pos:])
                    break
                pieces.append(line[pos:opening])
                pos, in_comment = opening, True
        visible = "".join(pieces)
        output.append(visible)
        start = re.match(r"^ {0,3}(`{3,}|~{3,})", visible)
        if start:
            token = start.group(1)
            fence = (token[0], len(token))
    return "".join(output)


def iter_gjb_fences(text: str):
    """Yield (start, end, language, body) for uncommented top-level gjb-* fences.

    HTML comments are masked first, matching render_lines(). Opening/closing
    rules follow the renderer: backtick or tilde fences of length >= 3.
    Nested fences inside a non-gjb code block are ignored.
    """
    masked = mask_comments(text)
    lines = masked.splitlines(keepends=True)
    offset = 0
    fence = None
    capturing = False
    start = 0
    lang = ""
    chunks: list[str] = []
    for line in lines:
        current = offset
        offset += len(line)
        stripped = line.strip()
        if fence:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(fence[1]) + r",}\s*", stripped):
                if capturing:
                    yield start, offset, lang, "".join(chunks)
                fence = None
                capturing = False
                chunks = []
                lang = ""
            elif capturing:
                chunks.append(line)
            continue
        opening = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
        if opening:
            token = opening.group(1)
            info = opening.group(2).strip()
            fence = (token[0], len(token))
            if info.lower().startswith("gjb-"):
                capturing = True
                lang = info.split()[0].lower()
                start = current
                chunks = []


def strip_fenced_blocks(text: str) -> str:
    """Narrative accounting excludes code/evidence, including tilde fences."""
    result, fence = [], None
    for line in mask_comments(text).splitlines(keepends=True):
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) +
                            r"{" + str(fence[1]) + r",}\s*", line):
                fence = None
            result.append("\n" if line.endswith("\n") else "")
            continue
        start = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if start:
            token = start.group(1)
            fence = (token[0], len(token))
            result.append("\n" if line.endswith("\n") else "")
        else:
            result.append(line)
    return "".join(result)


def is_back_matter_title(title: str) -> bool:
    value = re.sub(r"[*_`]", "", title).strip()
    value = re.sub(r"^\d+(?:\.\d+)*[.、．：:)]?\s*", "", value)
    return bool(re.match(
        r"^(?:附\s*录|附\s*件|appendi(?:x|ces)\b|annex(?:es)?\b|"
        r"质量门禁数据块|结构化工程证据|结构化证据正文展开)", value, re.I))


def headings(text: str):
    """Yield (line index, source offset, level, title, setext) outside fences."""
    clean = mask_comments(text)
    lines = clean.splitlines(keepends=True)
    offset = 0
    fence = None
    consumed = -1
    for i, line in enumerate(lines):
        current_offset = offset
        offset += len(line)
        if i == consumed:
            continue
        if fence:
            if re.fullmatch(r" {0,3}" + re.escape(fence[0]) +
                            r"{" + str(fence[1]) + r",}\s*", line):
                fence = None
            continue
        start = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if start:
            token = start.group(1)
            fence = (token[0], len(token))
            continue
        stripped_nl = line.rstrip("\r\n")
        # Closing ATX hashes require whitespace, so "# 3 C#" keeps the
        # language name. A space then hashes ("# 4 Title #") still closes.
        atx = re.match(r"^ {0,3}(#{1,9})\s+(.*?)(?:[ \t]+#+)?[ \t]*$", stripped_nl)
        if atx:
            yield i, current_offset, len(atx.group(1)), atx.group(2), False
        elif line.strip() and not line.startswith(('    ', '\t')) and i + 1 < len(lines):
            underline = re.fullmatch(r" {0,3}(=+|-+)\s*", lines[i + 1])
            if underline:
                consumed = i + 1
                yield i, current_offset, 1 if underline.group(1)[0] == '=' else 2, line.strip(), True


@dataclass(frozen=True)
class ContentScope:
    prelude: str
    main: str
    back_matter: str
    main_start: int
    back_start: int


def main_body_line_span(raw: str, body: str) -> tuple[int, int]:
    """1-based [first, last) line numbers of main body inside `raw`."""
    scope = split_content(body)
    offset = len(raw) - len(body)
    first = raw.count("\n", 0, offset + scope.main_start) + 1
    last = raw.count("\n", 0, offset + scope.back_start) + (1 if scope.back_matter else 2)
    return first, last


def artifacts_in_main_body(document) -> list:
    first, last = main_body_line_span(document.raw, document.body)
    selected = []
    for artifact in getattr(document, "artifacts", ()) or ():
        line = getattr(artifact, "line", None)
        try:
            line = int(line) if line is not None else None
        except (TypeError, ValueError):
            line = None
        if line is not None and first <= line < last:
            selected.append(artifact)
    return selected


def artifacts_of_main(document, kind: str) -> list:
    wanted = kind.lower().replace("_", "-")
    return [
        artifact for artifact in artifacts_in_main_body(document)
        if str(getattr(artifact, "kind", "")).lower().replace("_", "-") == wanted
    ]


def split_content(text: str) -> ContentScope:
    start, end = 0, len(text)
    found_main = False
    for _, offset, level, title, _ in headings(text):
        if is_back_matter_title(title):
            end = offset
            break  # Numbered headings later in an appendix never reopen main.
        if not found_main and level == 1 and re.match(r"^1(?:\s+|[.、．]\s*[^\d])", title):
            start, found_main = offset, True
    return ContentScope(text[:start], text[start:end], text[end:], start, end)


def render_lines(text: str) -> list[str]:
    """Normalize supported heading spelling, leaving source content untouched."""
    lines = mask_comments(text).splitlines()
    for index, _, level, title, setext in headings(text):
        lines[index] = '#' * level + ' ' + title
        if setext:
            lines[index + 1] = ''
    return lines


def mark_scope(paragraph, name: str, ident: int) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    start, end = OxmlElement('w:bookmarkStart'), OxmlElement('w:bookmarkEnd')
    start.set(qn('w:id'), str(ident))
    start.set(qn('w:name'), name)
    end.set(qn('w:id'), str(ident))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)
