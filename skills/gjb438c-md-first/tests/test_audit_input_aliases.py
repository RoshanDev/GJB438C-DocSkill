"""Audit input roles must never overwrite another role's original snapshot."""
import json
import os
from pathlib import Path
import pytest
from gjb438c_suite import cli
from gjb438c_suite.publication import PublicationError
from gjb438c_suite.volume import sha256_file


@pytest.mark.parametrize('role', ['source', 'baseline'])
@pytest.mark.parametrize('alias', ['same', 'relative', 'symlink', 'hardlink'])
def test_register_cannot_alias_another_input_after_content_audit(tmp_path, monkeypatch, role, alias):
    source = tmp_path / 'OCD.md'; baseline = tmp_path / 'SDP.md'
    for code, path in [('OCD', source), ('SDP', baseline)]:
        assert cli.main(['init', '--type', code, '--output', str(path)]) == 0
    monkeypatch.setattr(cli, 'load_baselines', lambda *a, **k: {'SDP': baseline})
    monkeypatch.setattr(cli, 'validate_baselines', lambda *a, **k: ([], {}))
    target = source if role == 'source' else baseline
    register = target
    if alias == 'relative':
        monkeypatch.chdir(tmp_path)
        register = Path(target.name)
    elif alias in {'symlink', 'hardlink'}:
        register = tmp_path / 'source-register.md'
        if alias == 'symlink': os.symlink(target, register)
        else: os.link(target, register)
    original = cli.audit_markdown_with_profile
    def audit(*args, **kwargs):
        report = original(*args, **kwargs)
        target.write_bytes(target.read_bytes() + b'\nchanged before register read\n')
        return report
    monkeypatch.setattr(cli, 'audit_markdown_with_profile', audit)
    output = tmp_path / 'audit.json'; output.write_bytes(b'{"passed":false,"old":true}')
    assert cli.main(['audit', str(source), '--profile=draft', '--source-register', str(register),
                     '--json', str(output)]) != 0
    assert json.loads(output.read_text(encoding='utf-8')) == {'passed': False, 'old': True}


def test_hash_binding_rejects_collisions_even_if_the_new_digest_differs(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'old')
    hashes = {}
    cli._bind_audit_input(hashes, source, sha256_file(source))
    initial = dict(hashes)
    source.write_bytes(b'changed')
    with pytest.raises(PublicationError, match='distinct'):
        cli._bind_audit_input(hashes, source, sha256_file(source))
    assert hashes == initial


def test_hash_binding_rejects_late_hardlink_alias(tmp_path):
    source = tmp_path / 'source'; source.write_bytes(b'old')
    register = tmp_path / 'register'
    hashes = {}
    cli._bind_audit_input(hashes, source, sha256_file(source))
    os.link(source, register)
    with pytest.raises(PublicationError, match='alias'):
        cli._bind_audit_input(hashes, register, sha256_file(register))
    assert len(hashes) == 1
