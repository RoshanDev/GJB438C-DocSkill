"""Office integration: no estimated page counts or simulated green releases."""
from pathlib import Path
import os,shutil
from zipfile import ZipFile,ZIP_DEFLATED
import pytest
from gjb438c_suite.render import render_document
from gjb438c_suite.finalize import refresh_toc_cache
from gjb438c_suite.import_word import import_word
from gjb438c_suite.audit_docx import audit_docx
from gjb438c_suite.volume import rendered_page_metrics,audit_rendered_volume,VolumeError

OFFICE=bool(os.environ.get('GJB_OFFICE_TESTS')) and bool(shutil.which('libreoffice') or shutil.which('soffice'))


@pytest.mark.skipif(not OFFICE,reason='set GJB_OFFICE_TESTS=1 with LibreOffice/UNO available')
def test_actual_office_body_start_and_roundtrip(tmp_path):
    source=Path(__file__).resolve().parents[1]/'examples/SRS.example.md'
    word=tmp_path/'sample.docx'
    render_document(source,word,profile='review')
    refresh_toc_cache(word)
    assert audit_docx(word,profile='release').passed
    metrics=rendered_page_metrics(word)
    assert metrics.body_start_page>=5 and metrics.body_pages>0
    returned=tmp_path/'returned.md'
    assert import_word(word,returned).exact_round_trip
    assert returned.read_bytes()==source.read_bytes()
    # This SMALL preview must not masquerade as a production large release.
    result=audit_rendered_volume(source,'SRS',word,tier='large')
    assert not result.passed
    changed=tmp_path/'changed.docx'
    with ZipFile(word) as src,ZipFile(changed,'w',ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data=src.read(info.filename)
            if info.filename=='word/document.xml':
                data=data.replace('任务管理'.encode(),'变更管理'.encode())
            dst.writestr(info,data)
    with pytest.raises(VolumeError,match='可见正文已修改'):
        audit_rendered_volume(source,'SRS',changed,tier='large')
    assert not import_word(changed,tmp_path/'candidate.md').exact_round_trip
