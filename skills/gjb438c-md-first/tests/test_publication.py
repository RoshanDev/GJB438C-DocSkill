from pathlib import Path
import os
import pytest
from gjb438c_suite import publication as pub


def release_set(tmp_path):
    targets, sources = [], []
    for name in ('content.json', 'audit.json', 'volume.json', 'output.docx'):
        t, s = tmp_path / name, tmp_path / ('new-' + name)
        t.write_bytes(b'old-' + name.encode()); s.write_bytes(b'new-' + name.encode())
        targets.append(t); sources.append(s)
    return dict(zip(targets, sources)), targets[-1]


def test_publish_docx_last(tmp_path, monkeypatch):
    files, marker = release_set(tmp_path); calls=[]; real=os.replace
    def replace(source, target):
        calls.append(Path(target)); return real(source,target)
    monkeypatch.setattr(pub.os, 'replace', replace)
    pub.publish_files(files, marker=marker)
    assert calls[-1] == marker
    assert set(calls) == set(files)
    assert all(p.read_bytes() == s.read_bytes() for p,s in files.items())
    assert not list(tmp_path.glob('*.lock'))


@pytest.mark.parametrize('point', range(4))
@pytest.mark.parametrize('failure', ['replace', 'file-fsync', 'dir-fsync'])
def test_release_set_rollback_at_each_publication_step(tmp_path, monkeypatch, point, failure):
    files, marker = release_set(tmp_path)
    before={p:p.read_bytes() for p in files}; real_replace=os.replace
    real_file=pub._fsync_file; real_dir=pub._fsync_dir
    count=0; armed=False; raised=False
    def replace(source,target):
        nonlocal count,armed,raised
        if Path(source).suffix == '.stage':
            armed = count == point; count += 1
            if armed and failure=='replace' and not raised:
                raised=True; raise OSError('injected replacement failure')
        return real_replace(source,target)
    def file_sync(path):
        nonlocal raised
        if armed and failure=='file-fsync' and path in files and not raised:
            raised=True; raise OSError('injected post-replace file fsync')
        return real_file(path)
    def dir_sync(path):
        nonlocal raised
        if armed and failure=='dir-fsync' and not raised:
            raised=True; raise OSError('injected post-replace directory fsync')
        return real_dir(path)
    monkeypatch.setattr(pub.os,'replace',replace)
    monkeypatch.setattr(pub,'_fsync_file',file_sync)
    monkeypatch.setattr(pub,'_fsync_dir',dir_sync)
    with pytest.raises(pub.PublicationError): pub.publish_files(files,marker=marker)
    assert raised
    assert {p:p.read_bytes() for p in files} == before


def test_missing_report_never_touches_existing_docx(tmp_path):
    files,marker=release_set(tmp_path); before={p:p.read_bytes() for p in files}
    next(iter(files.values())).unlink()
    with pytest.raises(pub.PublicationError): pub.publish_files(files,marker=marker)
    assert {p:p.read_bytes() for p in files} == before


def test_new_release_rollback_removes_new_files(tmp_path, monkeypatch):
    files, marker=release_set(tmp_path)
    for p in files:p.unlink()
    real=pub._fsync_file
    def fail(path):
        if path==marker:raise OSError('marker fsync')
        real(path)
    monkeypatch.setattr(pub,'_fsync_file',fail)
    with pytest.raises(pub.PublicationError):pub.publish_files(files,marker=marker)
    assert all(not p.exists() for p in files)


def test_alias_paths_rejected(tmp_path):
    path=tmp_path/'file';path.write_bytes(b'old')
    with pytest.raises(pub.PublicationError):pub.distinct_paths([path,path.parent/'a/../file'])
    if hasattr(os,'link'):
        alias=tmp_path/'hard';os.link(path,alias)
        with pytest.raises(pub.PublicationError):pub.distinct_paths([path,alias])


def test_cooperating_writer_lock_is_exclusive(tmp_path):
    files,marker=release_set(tmp_path)
    with pub._locks(list(files)):
        with pytest.raises(pub.PublicationError,match='locked'):pub.publish_files(files,marker=marker)
