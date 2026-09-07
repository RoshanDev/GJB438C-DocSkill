"""Non-text edits must never qualify for exact or front-only body preservation."""
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree
from PIL import Image
import pytest

from gjb438c_suite.body_binding import DOCVAR_STRUCTURE_HASH
from gjb438c_suite.import_word import import_word
from gjb438c_suite.markdown_doc import parse_markdown
from gjb438c_suite.render import render_document, _normalized_bookmark_text, NS, W
from gjb438c_suite.volume import _binding, VolumeError
from test_front_binding import SOURCE, _rewrite, _edit_text


@pytest.fixture
def illustrated(tmp_path):
    image = tmp_path / 'example.png'
    Image.new('RGB', (4, 4), 'white').save(image)
    source = tmp_path / 'SRS.md'
    source.write_text(SOURCE.read_text(encoding='utf-8') + '\n\n![fixture](example.png)\n', encoding='utf-8')
    word = tmp_path / 'SRS.docx'
    render_document(source, word, profile='review')
    _binding(parse_markdown(source), word)
    returned = tmp_path / 'unchanged.md'
    assert import_word(word, returned).exact_round_trip
    assert source.read_bytes() == returned.read_bytes()
    return source, word


def _change_nontext(word, kind):
    with ZipFile(word) as z:
        data = {n: z.read(n) for n in z.namelist()}
    if kind == 'media':
        stream = BytesIO()
        Image.new('RGB', (4, 4), 'black').save(stream, format='PNG')
        data[next(n for n in data if n.startswith('word/media/'))] = stream.getvalue()
    elif kind == 'relationship':
        ns = '{http://schemas.openxmlformats.org/package/2006/relationships}'
        root = etree.fromstring(data['word/_rels/document.xml.rels'])
        rel = next(n for n in root.findall(ns + 'Relationship') if n.get('Type', '').endswith('/image'))
        original = 'word/' + rel.get('Target')
        data['word/media/replaced.png'] = data[original]
        rel.set('Target', 'media/replaced.png')
        data['word/_rels/document.xml.rels'] = etree.tostring(root)
    else:
        root = etree.fromstring(data['word/document.xml'])
        if kind == 'drawing':
            # The front template also contains a drawing. Mutate the real
            # body image after GJB_BODY, not that unrelated cover shape.
            body = root.find('./w:body', NS)
            start = body.xpath('.//w:bookmarkStart[@w:name="GJB_BODY"]', namespaces=NS)[0]
            node = start
            while node.getparent() is not body:
                node = node.getparent()
            tag = '{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}extent'
            extent = next(e for child in list(body)[body.index(node):] for e in child.iter(tag))
            before = int(extent.get('cx'))
            assert before > 1
            extent.set('cx', str(before // 2))
        elif kind == 'table':
            body = root.find('./w:body', NS)
            start = body.xpath('.//w:bookmarkStart[@w:name="GJB_BODY"]', namespaces=NS)[0]
            node = start
            while node.getparent() is not body:
                node = node.getparent()
            table = next(n for n in list(body)[body.index(node):] if n.tag == f'{{{W}}}tbl')
            cell = table.find('.//w:tcPr', NS)
            etree.SubElement(cell, f'{{{W}}}gridSpan').set(f'{{{W}}}val', '2')
        else:
            body = root.find('./w:body', NS)
            paragraph = etree.Element(f'{{{W}}}p')
            run = etree.SubElement(paragraph, f'{{{W}}}r')
            etree.SubElement(run, f'{{{W}}}t').text = 'appended outside the original closing bookmark'
            body.insert(len(body) - 1, paragraph)
        data['word/document.xml'] = etree.tostring(root)
    with ZipFile(word, 'w', ZIP_DEFLATED) as z:
        for name, value in data.items():
            z.writestr(name, value)


@pytest.mark.parametrize('kind', ['media', 'relationship', 'drawing', 'table', 'appended'])
@pytest.mark.parametrize('front_changed', [False, True])
def test_nontext_or_untracked_body_edit_invalidates_preservation(tmp_path, illustrated, kind, front_changed):
    source, word = illustrated
    with ZipFile(word) as z:
        text_before = _normalized_bookmark_text(z.read('word/document.xml'))
    _change_nontext(word, kind)
    if front_changed:
        _rewrite(word, lambda root: _edit_text(root, 'DEMO-SRS-001'))
    with ZipFile(word) as z:
        assert _normalized_bookmark_text(z.read('word/document.xml')) == text_before
    with pytest.raises(VolumeError, match='正文结构或图片资源'):
        _binding(parse_markdown(source), word)
    returned = tmp_path / 'returned.md'
    result = import_word(word, returned)
    assert not result.exact_round_trip
    metadata = parse_markdown(returned).metadata
    assert metadata['round_trip']['body_preserved'] is False
    assert metadata['round_trip']['body_structure_verified'] is False
    assert metadata['document']['status'] == 'draft'
    assert 'approval' not in metadata


@pytest.mark.parametrize('remove', [True, False])
def test_missing_or_bad_structural_binding_does_not_guess_unchanged(tmp_path, illustrated, remove):
    source, word = illustrated
    def modify(root):
        node = next(n for n in root.xpath('./w:docVars/w:docVar', namespaces=NS)
                    if n.get(f'{{{W}}}name') == DOCVAR_STRUCTURE_HASH)
        if remove:
            node.getparent().remove(node)
        else:
            node.set(f'{{{W}}}val', '0' * 64)
    _rewrite(word, modify, 'word/settings.xml')
    with pytest.raises(VolumeError, match='正文结构或图片资源'):
        _binding(parse_markdown(source), word)
    returned = tmp_path / 'returned.md'
    assert not import_word(word, returned).exact_round_trip
    assert parse_markdown(returned).metadata['round_trip']['body_preserved'] is False
