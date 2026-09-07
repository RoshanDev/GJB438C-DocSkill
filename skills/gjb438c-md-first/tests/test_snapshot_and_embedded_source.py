"""Snapshot coherence and hidden Markdown integrity must precede certification."""
import base64
import gzip
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from lxml import etree
import pytest

from gjb438c_suite import cli, import_word, profile_quality
from gjb438c_suite.render import DOCVAR_PREFIX, DOCVAR_SOURCE_HASH, NS, W
from gjb438c_suite.volume import sha256_file


def test_template_and_audit_must_use_identical_source(tmp_path, monkeypatch):
    source = tmp_path / 'OCD.md'
    assert cli.main(['init', '--type', 'OCD', '--output', str(source)]) == 0
    target = tmp_path / 'out.docx'; target.write_bytes(b'previous release')
    resolver = cli.resolve_front_template
    def change_after_selection(document, override):
        result = resolver(document, override)
        source.write_bytes(source.read_bytes().replace(b'status: draft', b'status: changed'))
        return result
    monkeypatch.setattr(cli, 'resolve_front_template', change_after_selection)
    monkeypatch.setattr(cli, '_audit_all', lambda a: ({'passed': True, 'provenance': {
        'source_sha256': sha256_file(source), 'baseline_sha256': {}}}, 'OCD', 'large', 80, None))
    monkeypatch.setattr(cli, 'render_document', lambda *a, **k: pytest.fail('inconsistent snapshot must never render'))
    assert cli.main(['render', str(source), '--output', str(target), '--profile=release']) == 2
    assert target.read_bytes() == b'previous release'


def test_content_audit_detects_source_edit_during_checks(tmp_path, monkeypatch):
    source = tmp_path / 'OCD.md'
    assert cli.main(['init', '--type', 'OCD', '--output', str(source)]) == 0
    expected = sha256_file(source)
    audit = cli.audit_markdown_with_profile
    def edit(*args, **kwargs):
        report = audit(*args, **kwargs)
        source.write_bytes(source.read_bytes() + b'\nChanged during audit\n')
        return report
    monkeypatch.setattr(cli, 'audit_markdown_with_profile', edit)
    output = tmp_path / 'audit.json'
    assert cli.main(['audit', str(source), '--profile=draft', '--json', str(output)]) == 2
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['provenance']['source_sha256'] == expected
    assert any(x['code'] == 'AUDIT_INPUT_CHANGED' for x in report['preflight'])


@pytest.mark.parametrize('change', ['source_chunk', 'missing_hash', 'wrong_hash'])
def test_unverified_embedded_source_cannot_be_imported_as_exact(tmp_path, change):
    source = tmp_path / 'OCD.md'; docx = tmp_path / 'OCD.docx'
    assert cli.main(['init', '--type', 'OCD', '--output', str(source)]) == 0
    assert cli.main(['render', str(source), '--profile=draft', '--output', str(docx)]) == 0
    with ZipFile(docx) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    settings = etree.fromstring(parts['word/settings.xml'])
    variables = settings.xpath('./w:docVars/w:docVar', namespaces=NS)
    source_hash = next(x for x in variables if x.get(f'{{{W}}}name') == DOCVAR_SOURCE_HASH)
    if change == 'missing_hash':
        source_hash.getparent().remove(source_hash)
    elif change == 'wrong_hash':
        source_hash.set(f'{{{W}}}val', '0' * 64)
    else:
        chunks = sorted([x for x in variables if x.get(f'{{{W}}}name', '').startswith(DOCVAR_PREFIX)
                         and x.get(f'{{{W}}}name', '')[-4:].isdigit()], key=lambda x: x.get(f'{{{W}}}name'))
        altered = source.read_bytes().replace(b'status: draft', b'status: approved\napproval:\n  reviewer: forged')
        assert altered != source.read_bytes()
        encoded = base64.b64encode(gzip.compress(altered)).decode('ascii')
        chunks[0].set(f'{{{W}}}val', encoded)
        for node in chunks[1:]: node.getparent().remove(node)
    parts['word/settings.xml'] = etree.tostring(settings, xml_declaration=True, encoding='UTF-8')
    with ZipFile(docx, 'w', ZIP_DEFLATED) as archive:
        for name, value in parts.items(): archive.writestr(name, value)
    candidate = tmp_path / 'candidate.md'
    result = import_word.import_word(docx, candidate)
    assert not result.exact_round_trip
    text = candidate.read_text(encoding='utf-8')
    assert 'status: draft' in text and 'approval:' not in text and 'forged' not in text
