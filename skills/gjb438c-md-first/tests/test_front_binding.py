"""Cover/signatures/revisions must remain bound when the body is unchanged."""
from copy import deepcopy
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree
import pytest

from gjb438c_suite import cli, suite, volume
from gjb438c_suite.import_word import import_word
from gjb438c_suite.markdown_doc import parse_markdown
from gjb438c_suite.render import (
    DOCVAR_FRONT_HASH, NS, W, _normalized_bookmark_text, render_document,
)
from test_review_round_three import _passing_suite


SOURCE = Path(__file__).resolve().parents[1] / 'examples/SRS.example.md'


def _rewrite(path, transform, part='word/document.xml'):
    with ZipFile(path) as archive:
        content = {name: archive.read(name) for name in archive.namelist()}
    root = etree.fromstring(content[part])
    transform(root)
    content[part] = etree.tostring(root, encoding='UTF-8', xml_declaration=True)
    with ZipFile(path, 'w', ZIP_DEFLATED) as archive:
        for name, data in content.items():
            archive.writestr(name, data)


def _edit_text(root, fragment):
    node = next(n for n in root.xpath('.//w:t', namespaces=NS) if fragment in (n.text or ''))
    node.text = node.text.replace(fragment, fragment + ' [changed by Word]', 1)


@pytest.mark.parametrize('fragment', [
    'DEMO-SRS-001', '公开', 'V1.0', '软件需求规格说明', '示例任务管理软件',
    '二〇二六年九月', '编制：', '审核：', '批准：', '建立软件需求规格说明示例', '示例项目组',
])
def test_front_edit_cannot_pass_binding_or_keep_exact_import(tmp_path, fragment):
    word = tmp_path / 'candidate.docx'
    render_document(SOURCE, word, profile='review')
    volume._binding(parse_markdown(SOURCE), word)
    with ZipFile(word) as archive:
        body_before = _normalized_bookmark_text(archive.read('word/document.xml'))
    _rewrite(word, lambda root: _edit_text(root, fragment))
    with ZipFile(word) as archive:
        assert body_before == _normalized_bookmark_text(archive.read('word/document.xml'))
    with pytest.raises(volume.VolumeError, match='前三页'):
        volume._binding(parse_markdown(SOURCE), word)
    returned = tmp_path / 'returned.md'
    result = import_word(word, returned)
    assert not result.exact_round_trip
    imported = parse_markdown(returned)
    original = parse_markdown(SOURCE)
    assert imported.body == original.body
    assert [(a.kind, a.data) for a in imported.artifacts] == [(a.kind, a.data) for a in original.artifacts]
    metadata = imported.metadata
    assert metadata['round_trip']['body_preserved'] is True
    assert metadata['document']['status'] == 'draft'
    assert 'approval' not in metadata
    assert metadata['round_trip']['front_matter_review_required'] is True
    assert '[changed by Word]' in str(metadata['round_trip']['observed_front_paragraphs'])


@pytest.mark.parametrize('change', ['missing', 'wrong'])
def test_missing_or_wrong_front_binding_fails_closed(tmp_path, change):
    word = tmp_path / 'candidate.docx'
    render_document(SOURCE, word, profile='review')
    def alter(root):
        entry = next(n for n in root.xpath('./w:docVars/w:docVar', namespaces=NS)
                     if n.get(f'{{{W}}}name') == DOCVAR_FRONT_HASH)
        if change == 'missing':
            entry.getparent().remove(entry)
        else:
            entry.set(f'{{{W}}}val', '0' * 64)
    _rewrite(word, alter, 'word/settings.xml')
    with pytest.raises(volume.VolumeError, match='前三页'):
        volume._binding(parse_markdown(SOURCE), word)
    returned = tmp_path / 'returned.md'
    assert not import_word(word, returned).exact_round_trip
    assert parse_markdown(returned).body == parse_markdown(SOURCE).body
    assert parse_markdown(returned).metadata['round_trip']['body_preserved'] is True


def test_front_run_splitting_is_not_a_content_edit(tmp_path):
    word = tmp_path / 'document.docx'
    render_document(SOURCE, word, profile='review')
    def split(root):
        node = next(n for n in root.xpath('.//w:t', namespaces=NS) if n.text == 'DEMO-SRS-001')
        run = node.getparent()
        other = deepcopy(run)
        node.text = 'DEMO-'
        other.find(f'{{{W}}}t').text = 'SRS-001'
        run.addnext(other)
    _rewrite(word, split)
    volume._binding(parse_markdown(SOURCE), word)
    returned = tmp_path / 'returned.md'
    assert import_word(word, returned).exact_round_trip
    assert SOURCE.read_bytes() == returned.read_bytes()


def test_audit_volume_rejects_front_edit_before_office_and_keeps_old_report(tmp_path, monkeypatch):
    word = tmp_path / 'candidate.docx'
    render_document(SOURCE, word, profile='review')
    _rewrite(word, lambda root: _edit_text(root, 'DEMO-SRS-001'))
    monkeypatch.setattr(volume, 'rendered_page_metrics', lambda *a, **k: pytest.fail('changed cover must fail before Office'))
    report = tmp_path / 'volume.json'
    report.write_bytes(b'previous report')
    assert cli.main(['audit-volume', str(word), '--source', str(SOURCE),
                     '--tier', 'large', '--json', str(report)]) != 0
    assert report.read_bytes() == b'previous report'


def test_suite_rejects_front_edit_even_with_rehashed_volume_json(tmp_path, monkeypatch):
    manifest, measure = _passing_suite(tmp_path, monkeypatch)
    source, word = tmp_path / 'OCD.md', tmp_path / 'OCD.docx'
    # The surrounding fixture isolates suite orchestration. Binding uses a real
    # generated DOCX and the real volume audit, before slow Office measurement.
    # Use the public example's populated cover for this guard-only fixture.
    source.write_text(SOURCE.read_text(encoding='utf-8').replace('type: SRS', 'type: OCD')
                      .replace('identifier: DEMO-CSCI', 'identifier: DEMO'), encoding='utf-8')
    render_document(source, word, profile='draft')
    volume._binding(parse_markdown(source), word)
    root_before = None
    with ZipFile(word) as archive:
        root_before = _normalized_bookmark_text(archive.read('word/document.xml'))
    _rewrite(word, lambda root: _edit_text(root, '编制：'))
    with ZipFile(word) as archive:
        assert root_before == _normalized_bookmark_text(archive.read('word/document.xml'))
    persisted = tmp_path / 'OCD.json'
    data = json.loads(persisted.read_text())
    data['docx_sha256'] = volume.sha256_file(word)
    data['source_sha256'] = volume.sha256_file(source)
    persisted.write_text(json.dumps(data), encoding='utf-8')
    def audit(document, code, path, **kw):
        if code == 'OCD':
            return volume.audit_rendered_volume(document, code, path, **kw)
        return measure(document, code, path, **kw)
    monkeypatch.setattr(suite, 'audit_rendered_volume', audit)
    output = tmp_path / 'suite-result.json'
    assert cli.main(['audit-suite', str(manifest), '--json', str(output)]) == 5
    result = json.loads(output.read_text())
    assert result['passed'] is False
    assert any(i['code'] == 'SUITE_RELEASE_AUDIT_FAILED' and '前三页' in i['message']
               for i in result['issues'])


@pytest.mark.parametrize('change', ['body', 'embedded'])
def test_cover_recovery_never_restores_an_unverified_body(tmp_path, change):
    word = tmp_path / 'changed.docx'
    render_document(SOURCE, word, profile='review')
    _rewrite(word, lambda root: _edit_text(root, 'DEMO-SRS-001'))
    if change == 'body':
        _rewrite(word, lambda root: _edit_text(root, '1.1 标识'))
    else:
        from gjb438c_suite.render import DOCVAR_SOURCE_HASH
        def alter(root):
            node = next(n for n in root.xpath('./w:docVars/w:docVar', namespaces=NS)
                        if n.get(f'{{{W}}}name') == DOCVAR_SOURCE_HASH)
            node.set(f'{{{W}}}val', '0' * 64)
        _rewrite(word, alter, 'word/settings.xml')
    returned = tmp_path / 'candidate.md'
    assert not import_word(word, returned).exact_round_trip
    candidate = parse_markdown(returned)
    assert candidate.metadata['round_trip']['body_preserved'] is False
    assert candidate.body != parse_markdown(SOURCE).body
    assert candidate.metadata['document']['status'] == 'draft'
    assert 'approval' not in candidate.metadata
