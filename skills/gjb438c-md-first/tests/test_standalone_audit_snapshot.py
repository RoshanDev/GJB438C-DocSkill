"""Standalone audit must not publish PASS after its inputs have changed."""
import json
from pathlib import Path
import pytest
from gjb438c_suite import cli, publication
from gjb438c_suite.volume import sha256_file


@pytest.mark.parametrize('victim', ['source', 'baseline', 'register'])
@pytest.mark.parametrize('stage', ['register_scan', 'after_audit', 'publication_stage'])
def test_standalone_json_rejects_late_input_edits(tmp_path, monkeypatch, victim, stage):
    source = tmp_path / 'OCD.md'
    baseline = tmp_path / 'SDP.md'
    register = tmp_path / 'source-register.md'
    report_path = tmp_path / 'audit.json'
    for code, path in [('OCD', source), ('SDP', baseline)]:
        assert cli.main(['init', '--type', code, '--output', str(path)]) == 0
    register.write_bytes(b'SRC-TEST registered')
    report_path.write_text('{"passed": false, "old": true}', encoding='utf-8')
    monkeypatch.setattr(cli, 'load_baselines', lambda *a, **k: {'SDP': baseline})
    monkeypatch.setattr(cli, 'validate_baselines', lambda *a, **k: ([], {'SDP': sha256_file(baseline)}))
    target = {'source': source, 'baseline': baseline, 'register': register}[victim]
    old = target.read_bytes()
    def mutate(): target.write_bytes(old + b'\nchanged after initial checks\n')
    if stage == 'register_scan':
        original = Path.read_bytes
        def read(path):
            data = original(path)
            if path == register: mutate()
            return data
        monkeypatch.setattr(Path, 'read_bytes', read)
    elif stage == 'after_audit':
        original = cli._audit_all
        def audit(*args):
            result = original(*args)
            assert result[0]['passed']
            mutate()
            return result
        monkeypatch.setattr(cli, '_audit_all', audit)
    else:
        original = publication.shutil.copyfile
        def copy(a, b, *args, **kwargs):
            result = original(a, b, *args, **kwargs)
            mutate()
            return result
        monkeypatch.setattr(publication.shutil, 'copyfile', copy)
    assert cli.main(['audit', str(source), '--profile=draft', '--source-register', str(register),
                     '--json', str(report_path)]) != 0
    assert json.loads(report_path.read_text(encoding='utf-8'))['passed'] is False


def test_stdout_only_audit_revalidates_after_serialization(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'OCD.md'
    assert cli.main(['init', '--type', 'OCD', '--output', str(source)]) == 0
    original = cli._audit_all
    def audit(*args):
        result = original(*args)
        assert result[0]['passed']
        source.write_bytes(source.read_bytes() + b'\nlate edit\n')
        return result
    monkeypatch.setattr(cli, '_audit_all', audit)
    capsys.readouterr()
    assert cli.main(['audit', str(source), '--profile=draft']) != 0
    assert '"passed": true' not in capsys.readouterr().out
