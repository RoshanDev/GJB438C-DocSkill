from pathlib import Path
import json
from types import SimpleNamespace
import pytest
from gjb438c_suite import cli
from gjb438c_suite.registry import iter_document_types
from gjb438c_suite.volume import sha256_file

OPTIONS=[['--profile','release'],['--profile=release'],['--profile=review','--profile=release'],
         ['--profile','review','--profile=release'],['--profile=review','--profile','release']]


@pytest.mark.parametrize('options',OPTIONS)
def test_release_final_option_never_delegates_to_unguarded_renderer(tmp_path,monkeypatch,options):
    source=tmp_path/'source.md';source.write_text('draft')
    target=tmp_path/'out.docx';target.write_bytes(b'previous')
    seen=[]
    def audit(args):
        seen.append(args.profile)
        return {'passed':False},'SRS','large',200,None
    monkeypatch.setattr(cli,'_audit_all',audit)
    monkeypatch.setattr(cli,'render_document',lambda *a,**k:pytest.fail('unguarded rendering'))
    assert cli.main(['render',str(source),'--output',str(target),*options])==2
    assert seen==['release'] and target.read_bytes()==b'previous'


@pytest.mark.parametrize('options',OPTIONS)
def test_release_cli_publishes_every_audit_report_with_docx_last(tmp_path,monkeypatch,options):
    source=tmp_path/'source.md';source.write_text('audited source')
    target=tmp_path/'out.docx';h=sha256_file(source)
    payload={'passed':True,'provenance':{'source_sha256':h,'baseline_sha256':{}}}
    monkeypatch.setattr(cli,'_audit_all',lambda a:(payload,'SRS','large',200,None))
    def render(source,target,**kwargs):target.write_bytes(b'DOCX after real content gate')
    monkeypatch.setattr(cli,'render_document',render)
    monkeypatch.setattr(cli,'refresh_toc_cache',lambda p:None)
    monkeypatch.setattr(cli,'audit_docx',lambda *a,**kw:SimpleNamespace(passed=True,as_dict=lambda:{'passed':True}))
    monkeypatch.setattr(cli,'audit_rendered_volume',lambda *a,**kw:SimpleNamespace(passed=True,as_dict=lambda:{'passed':True}))
    published=[]
    real=cli.publish_files
    def publish(files,*,marker):
        published.append((files.copy(),marker));return real(files,marker=marker)
    monkeypatch.setattr(cli,'publish_files',publish)
    assert cli.main(['render',str(source),'--output',str(target),*options])==0
    assert len(published)==1 and len(published[0][0])==4 and published[0][1]==target
    for suffix in ('.content.json','.audit.json','.volume.json'):
        assert json.loads(Path(str(target)+suffix).read_text())['passed']


def test_last_review_option_is_review():
    args=cli.build_parser().parse_args(['render','a','--output','b','--profile=release','--profile=review'])
    assert args.profile=='review'


@pytest.mark.parametrize('code',[x.code for x in iter_document_types()])
def test_all_twenty_draft_documents_render_roundtrip_but_fail_review(tmp_path,code):
    source=tmp_path/f'{code}.md';word=tmp_path/f'{code}.docx';back=tmp_path/f'{code}-back.md'
    assert cli.main(['init','--type',code,'--output',str(source)])==0
    assert cli.main(['audit',str(source),'--profile','review'])==2
    assert cli.main(['render',str(source),'--profile','draft','--output',str(word)])==0
    assert cli.main(['import-word',str(word),'--output',str(back)])==0
    assert source.read_bytes()==back.read_bytes()


def test_cannot_overwrite_input_with_report(tmp_path):
    source=tmp_path/'source.md'
    cli.main(['init','--type','OCD','--output',str(source)])
    before=source.read_bytes()
    assert cli.main(['audit',str(source),'--profile','draft','--json',str(source)])!=0
    assert source.read_bytes()==before
