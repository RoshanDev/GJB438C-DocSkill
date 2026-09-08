"""Regressions for PR5's second revision: input races, type override, template aliases.

Unit fixtures isolate the guards; real Office integration remains a separate job.
"""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from gjb438c_suite import cli, publication, suite, volume
from gjb438c_suite.markdown_doc import parse_markdown
from gjb438c_suite.registry import iter_document_types, default_front_matter_template
from gjb438c_suite.render import resolve_front_template


def _source(path, code='OCD', **overrides):
    meta = {'document': {'type': code}, 'software': {'identifier': 'DEMO'},
            'quality': {'tier': 'large'}, **overrides}
    path.write_text('---\n' + yaml.safe_dump(meta) + '---\n# 1 Scope\nCandidate content.\n', encoding='utf-8')
    return path


def _passing_suite(tmp_path, monkeypatch):
    codes = ['OCD', 'SDP']
    entries = {}
    for code in codes:
        source = _source(tmp_path / (code + '.md'), code)
        word = tmp_path / (code + '.docx')
        word.write_bytes(b'unit-test-only-docx-' + code.encode())
        report = tmp_path / (code + '.json')
        report.write_text(json.dumps({'passed': True, 'document_type': code, 'tier': 'large', 'page_count_scope': volume.PAGE_COUNT_SCOPE,
                                     'body_pages': 1000, 'appendix_pages': 0, 'appendix_start_page': None,
                                     'source_sha256': volume.sha256_file(source),
                                     'docx_sha256': volume.sha256_file(word)}), encoding='utf-8')
        entries[code] = {'markdown': source.name, 'docx': word.name, 'volume_report': report.name}
    decision = {'status': 'approved', 'rationale': 'unit fixture scope', 'impact': 'unit test only',
                'source_refs': ['SRC-TEST'], 'approved_by': 'fixture reviewer', 'approved_at': '2026-09-01'}
    manifest = tmp_path / 'suite.yaml'
    manifest.write_text(yaml.safe_dump({'suite': {'tier': 'large', 'required_documents': codes,
        'tailoring': {item.code: decision for item in iter_document_types() if item.code not in codes}},
        'documents': entries}), encoding='utf-8')
    ok = SimpleNamespace(passed=True, to_text=lambda: 'fixture')
    monkeypatch.setattr(suite, 'audit_markdown_with_profile', lambda *a, **k: ok)
    monkeypatch.setattr(volume, 'markdown_volume_issues', lambda *a, **k: [])
    monkeypatch.setattr(suite, 'audit_docx', lambda *a, **k: ok)
    def measure(document, code, word, **kwargs):
        data = {'passed': True, 'document_type': code, 'tier': 'large', 'page_count_scope': volume.PAGE_COUNT_SCOPE,
                'body_pages': 1000, 'appendix_pages': 0, 'appendix_start_page': None,
                'source_sha256': volume.sha256_text(document.raw), 'docx_sha256': volume.sha256_file(word)}
        return SimpleNamespace(passed=True, body_pages=1000, appendix_pages=0, appendix_start_page=None,
                               to_json=lambda: json.dumps(data), to_text=lambda: 'fixture')
    monkeypatch.setattr(suite, 'audit_rendered_volume', measure)
    return manifest, measure


def test_successful_suite_records_all_exact_input_hashes(tmp_path, monkeypatch):
    manifest, _ = _passing_suite(tmp_path, monkeypatch)
    report = suite.audit_suite_manifest(manifest)
    assert report.passed, report.to_text()
    assert len(report.input_sha256) == 7
    for path, digest in report.input_sha256.items():
        assert digest == volume.sha256_file(path)
    assert report.as_dict()['input_sha256'] == report.input_sha256


@pytest.mark.parametrize('name', ['OCD.md', 'OCD.docx', 'OCD.json', 'suite.yaml', 'SDP.docx'])
@pytest.mark.parametrize('mutation', ['edit', 'delete'])
def test_suite_rejects_input_change_during_later_office_check(tmp_path, monkeypatch, name, mutation):
    manifest, measure = _passing_suite(tmp_path, monkeypatch)
    changed = tmp_path / name
    before = volume.sha256_file(changed)
    def mutate(document, code, word, **kw):
        result = measure(document, code, word, **kw)
        if code == 'SDP':
            changed.unlink() if mutation == 'delete' else changed.write_bytes(b'changed after earlier check')
        return result
    monkeypatch.setattr(suite, 'audit_rendered_volume', mutate)
    report = suite.audit_suite_manifest(manifest)
    assert not report.passed
    assert any(issue.code == 'SUITE_INPUT_CHANGED' for issue in report.issues)
    assert report.input_sha256[str(changed)] == before


def test_suite_checks_generated_volume_report_at_end(tmp_path, monkeypatch):
    manifest, measure = _passing_suite(tmp_path, monkeypatch)
    def mutate(document, code, word, **kw):
        if code == 'SDP':
            (tmp_path / 'OCD.json').write_bytes(b'tampered generated report')
        return measure(document, code, word, **kw)
    monkeypatch.setattr(suite, 'audit_rendered_volume', mutate)
    report = suite.audit_suite_manifest(manifest, write_volume_reports=True)
    assert not report.passed
    assert any(x.code == 'SUITE_INPUT_CHANGED' for x in report.issues)


def test_cli_rechecks_suite_after_return_before_json(tmp_path, monkeypatch):
    manifest, _ = _passing_suite(tmp_path, monkeypatch)
    def after_audit(*a, **kw):
        report = suite.audit_suite_manifest(*a, **kw)
        assert report.passed
        manifest.write_bytes(b'manifest changed after return')
        return report
    monkeypatch.setattr(cli, 'audit_suite_manifest', after_audit)
    destination = tmp_path / 'suite-result.json'
    assert cli.main(['audit-suite', str(manifest), '--json', str(destination)]) == 5
    assert json.loads(destination.read_text(encoding='utf-8'))['passed'] is False


@pytest.mark.parametrize('when', ['stage', 'after_replace'])
def test_report_publication_rechecks_inputs_and_restores_old_report(tmp_path, monkeypatch, when):
    source = tmp_path / 'input.md'; source.write_bytes(b'audited')
    output = tmp_path / 'report.json'; output.write_bytes(b'previous report')
    expected = {str(source): volume.sha256_file(source)}
    if when == 'stage':
        original = publication.shutil.copyfile
        def copy(a, b, *args, **kwargs):
            result = original(a, b, *args, **kwargs)
            source.write_bytes(b'changed during staging')
            return result
        monkeypatch.setattr(publication.shutil, 'copyfile', copy)
    else:
        original = publication._fsync_file
        def flush(path):
            original(path)
            if path == output:
                source.write_bytes(b'changed after replace')
        monkeypatch.setattr(publication, '_fsync_file', flush)
    with pytest.raises(publication.PublicationError, match='audited input changed'):
        publication.write_report(output, '{"passed":true}', inputs=[source], expected_hashes=expected)
    assert output.read_bytes() == b'previous report'


@pytest.mark.parametrize('code', ['OCD', 'SRS'])
@pytest.mark.parametrize('bad_type', [None, 'UNKNOWN'])
def test_cli_type_override_reaches_baseline_validation_and_emits_json(tmp_path, code, bad_type):
    source = _source(tmp_path / 'candidate.md', code)
    text = source.read_text(encoding='utf-8')
    front, body = text[4:].split('---\n', 1)
    meta = yaml.safe_load(front)
    if bad_type is None:
        del meta['document']['type']
    else:
        meta['document']['type'] = bad_type
    source.write_text('---\n' + yaml.safe_dump(meta) + '---\n' + body, encoding='utf-8')
    destination = tmp_path / 'audit.json'
    result = cli.main(['audit', str(source), '--type', code, '--profile', 'review', '--json', str(destination)])
    assert result == 2  # Bad metadata/content stay rejected, not silently repaired.
    data = json.loads(destination.read_text(encoding='utf-8'))
    assert data['document_type'] == code and data['passed'] is False


@pytest.mark.parametrize('alias_kind', ['relative', 'absolute', 'hardlink'])
@pytest.mark.parametrize('output_option', ['--output', '--content-audit-json', '--docx-audit-json', '--volume-json'])
def test_metadata_template_is_protected_from_every_publication_output(tmp_path, monkeypatch, alias_kind, output_option):
    template = tmp_path / 'template.docx'
    template.write_bytes(default_front_matter_template().read_bytes())
    alias = template
    if alias_kind == 'hardlink':
        alias = tmp_path / 'alias.docx'
        os.link(template, alias)
    configured = template.name if alias_kind == 'relative' else str(template)
    source = _source(tmp_path / 'source.md', front_matter={'template': configured})
    before = template.read_bytes()
    monkeypatch.setattr(cli, '_audit_all', lambda *a: pytest.fail('alias must fail before audit/render'))
    args = ['render', str(source), '--profile=release', '--output', str(tmp_path / 'result.docx')]
    args += [output_option, str(alias)]
    assert cli.main(args) == 2
    assert template.read_bytes() == before


def test_missing_metadata_template_is_not_silently_replaced_by_default(tmp_path):
    source = _source(tmp_path / 'source.md', front_matter={'template': 'missing.docx'})
    with pytest.raises(Exception, match='configured front template does not exist'):
        resolve_front_template(parse_markdown(source))
