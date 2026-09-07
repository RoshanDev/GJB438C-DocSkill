"""Regressions for Codex review 5127875358 (JSON, outline, volume snapshots).

Snapshot tests mock only slow Office measurement, never the publication guard.
Real Office pagination and installed-wheel checks remain separate CI jobs.
"""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gjb438c_suite import cli, publication, suite, volume
from gjb438c_suite.markdown_doc import split_clause_title
from gjb438c_suite.profile_quality import audit_profile_document
from gjb438c_suite.registry import iter_document_types
from gjb438c_suite.profiles import heading_outline
from test_review_round_three import _passing_suite


@pytest.mark.parametrize('root', [None, [], ['entry'], True, False, 17, 1.5, 'report', {}])
def test_non_object_volume_report_is_a_failed_suite_json(tmp_path, monkeypatch, root):
    manifest, _ = _passing_suite(tmp_path, monkeypatch)
    (tmp_path / 'OCD.json').write_text(json.dumps(root), encoding='utf-8')
    output = tmp_path / 'suite-result.json'
    assert cli.main(['audit-suite', str(manifest), '--json', str(output)]) == 5
    data = json.loads(output.read_text(encoding='utf-8'))
    assert data['passed'] is False
    assert any(i['code'] == 'SUITE_REPORT_MISMATCH' and i['document_type'] == 'OCD'
               for i in data['issues'])


@pytest.mark.parametrize('code', [item.code for item in iter_document_types()])
@pytest.mark.parametrize('mutation', ['level', 'number', 'both', 'unnumbered'])
def test_profile_matches_actual_level_and_number_for_all_twenty_types(tmp_path, code, mutation):
    source = tmp_path / (code + '.md')
    assert cli.main(['init', '--type', code, '--output', str(source)]) == 0
    before = audit_profile_document(source, audit_profile='review')
    assert before.heading_coverage_percent == 100
    text = source.read_text(encoding='utf-8')
    static = [h for h in heading_outline(code) if h.number and 'X' not in h.number.upper() and 'Y' not in h.number.upper()]
    heading = next((h for h in static if h.level == 2), static[0])
    level, number, title = heading.level, heading.number, heading.title
    original = '#' * level + f' {number} {title}'
    wrong_level = 1 if level != 1 else 2
    changed = {
        'level': '#' * wrong_level + f' {number} {title}',
        'number': '#' * level + f' 99 {title}',
        'both': '#' * wrong_level + f' 99 {title}',
        'unnumbered': '#' * level + f' {title}',
    }[mutation]
    source.write_text(text.replace(original, changed, 1), encoding='utf-8')
    for mode in ('review', 'release'):
        after = audit_profile_document(source, audit_profile=mode)
        assert after.heading_coverage_percent < 100
        assert any(i.code == 'PROFILE_HEADING_MISSING' and f'编号 {number}' in i.message
                   and i.severity == 'ERROR' for i in after.issues)


def _volume_fixture(tmp_path, monkeypatch):
    source = tmp_path / 'OCD.md'
    assert cli.main(['init', '--type', 'OCD', '--output', str(source)]) == 0
    word = tmp_path / 'OCD.docx'
    word.write_bytes(b'unit-fixture-only-docx')
    profiles = tmp_path / 'profiles'
    profiles.mkdir()
    (profiles / 'ocd.yaml').write_bytes(b'unit-fixture-profile')
    monkeypatch.setattr(cli, 'profile_directory', lambda: profiles)
    output = tmp_path / 'volume.json'
    output.write_bytes(b'{"passed": false, "previous": true}')
    def measure(document, code, docx, **kwargs):
        data = {'passed': True, 'source_sha256': hashlib.sha256(document.raw.encode('utf-8')).hexdigest(),
                'docx_sha256': volume.sha256_file(docx)}
        return SimpleNamespace(**data, as_dict=lambda: dict(data))
    monkeypatch.setattr(cli, 'audit_rendered_volume', measure)
    args = ['audit-volume', str(word), '--source', str(source), '--json', str(output)]
    return source, word, profiles / 'ocd.yaml', output, args, measure


def test_volume_report_records_exact_snapshots(tmp_path, monkeypatch):
    source, word, profile, output, args, _ = _volume_fixture(tmp_path, monkeypatch)
    assert cli.main(args) == 0
    data = json.loads(output.read_text(encoding='utf-8'))
    assert data['passed'] is True
    assert data['input_sha256'] == {str(p): volume.sha256_file(p) for p in (source, word, profile)}
    assert data['source_sha256'] == data['input_sha256'][str(source)]
    assert data['docx_sha256'] == data['input_sha256'][str(word)]


@pytest.mark.parametrize('role', ['source', 'docx', 'profile'])
@pytest.mark.parametrize('change', ['edit', 'delete'])
@pytest.mark.parametrize('when', ['pagination', 'emission', 'stage', 'after_replace'])
def test_volume_audit_rejects_input_change_without_publishing_stale_pass(
        tmp_path, monkeypatch, capsys, role, change, when):
    source, word, profile, output, args, measure = _volume_fixture(tmp_path, monkeypatch)
    victim = {'source': source, 'docx': word, 'profile': profile}[role]
    previous = output.read_bytes()
    done = False
    def mutate():
        nonlocal done
        if not done:
            done = True
            if change == 'delete':
                victim.unlink()
            else:
                victim.write_bytes(victim.read_bytes() + b'\nchanged input\n')
    if when == 'pagination':
        def paginate(*a, **k):
            result = measure(*a, **k)
            mutate()
            return result
        monkeypatch.setattr(cli, 'audit_rendered_volume', paginate)
    elif when == 'emission':
        original = cli._emit
        def emit(*a, **k):
            mutate()
            return original(*a, **k)
        monkeypatch.setattr(cli, '_emit', emit)
    elif when == 'stage':
        original = publication.shutil.copyfile
        def copy(*a, **k):
            result = original(*a, **k)
            mutate()
            return result
        monkeypatch.setattr(publication.shutil, 'copyfile', copy)
    else:
        original = publication._fsync_file
        def flush(path):
            original(path)
            if path == output:
                mutate()
        monkeypatch.setattr(publication, '_fsync_file', flush)
    capsys.readouterr()
    assert cli.main(args) != 0
    assert output.read_bytes() == previous
    assert '"passed": true' not in capsys.readouterr().out


def test_stdout_volume_audit_checks_before_printing_success(tmp_path, monkeypatch, capsys):
    source, word, _, _, args, _ = _volume_fixture(tmp_path, monkeypatch)
    original = cli._emit
    def emit(*a, **k):
        word.write_bytes(b'late edit')
        return original(*a, **k)
    monkeypatch.setattr(cli, '_emit', emit)
    capsys.readouterr()
    assert cli.main(args[:-2]) != 0
    assert '"passed": true' not in capsys.readouterr().out


@pytest.mark.parametrize('field', ['source_sha256', 'docx_sha256'])
def test_volume_measurement_hash_must_match_captured_bytes(tmp_path, monkeypatch, field):
    _, _, _, output, args, measure = _volume_fixture(tmp_path, monkeypatch)
    old = output.read_bytes()
    def wrong_hash(*a, **k):
        result = measure(*a, **k)
        setattr(result, field, '0' * 64)
        return result
    monkeypatch.setattr(cli, 'audit_rendered_volume', wrong_hash)
    assert cli.main(args) != 0
    assert output.read_bytes() == old
