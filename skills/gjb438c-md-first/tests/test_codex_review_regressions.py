"""Executable regressions for PR5 reviews 5125744181 and 5125819457."""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import json
import re

import pytest
import yaml

from gjb438c_suite import cli, publication, volume
from gjb438c_suite.markdown_doc import Artifact, Heading, MarkdownDocument, parse_markdown, render_skeleton
from gjb438c_suite.profiles import heading_outline
from gjb438c_suite.profile_quality import audit_profile_document
from gjb438c_suite.registry import get_document_type, iter_document_types
from gjb438c_suite.references import reference_issues, selected_dependencies
from gjb438c_suite.import_word import import_word
from gjb438c_suite.render import render_document
from gjb438c_suite.suite import audit_suite_manifest, initialize_suite


def doc(code, *artifacts):
    return MarkdownDocument(Path(code+'.md'), '', {'document': {'type': code}}, '', artifacts=list(artifacts))


def artifact(kind, identifier, **fields):
    return Artifact(kind, {'id': identifier, **fields}, 1, 'gjb-'+kind)


@pytest.mark.parametrize(('code','kind'), [('STD','test-case'),('STP','test-item'),('SDD','design-unit')])
def test_many_cases_for_one_requirement_do_not_prove_full_coverage(code,kind):
    baseline=doc('SRS',artifact('requirement','REQ-1'),artifact('requirement','REQ-2'))
    source=doc(code,*(artifact(kind,f'CASE-{i}',requirements=['REQ-1']) for i in range(30)))
    issues=reference_issues(code,source,{'SRS':baseline})
    assert any(x['code']=='SUITE_BASELINE_COVERAGE_INCOMPLETE' and 'REQ-2' in x['message'] for x in issues)
    source.artifacts.append(artifact(kind,'CASE-FINAL',requirements=['REQ-2']))
    assert reference_issues(code,source,{'SRS':baseline})==[]


def test_test_report_must_account_for_every_selected_test_case():
    std=doc('STD',artifact('test-case','TC-1'),artifact('test-case','TC-2'))
    report=doc('STR',artifact('test-execution','RUN-1',test_case='TC-1'))
    issues=reference_issues('STR',report,{'STD':std})
    assert any(x['code']=='SUITE_BASELINE_COVERAGE_INCOMPLETE' for x in issues)


def test_system_design_cannot_borrow_software_or_rogue_requirement():
    sss=doc('SSS',artifact('requirement','SYS-1'))
    srs=doc('SRS',artifact('requirement','SW-1'))
    ocd=doc('OCD',artifact('requirement','ROGUE-1'))
    design=doc('SSDD',artifact('design-unit','DU-1',requirements=['SW-1','ROGUE-1']))
    issues=reference_issues('SSDD',design,{'SSS':sss,'SRS':srs,'OCD':ocd})
    assert sum(x['code']=='SUITE_REFERENCE_UNRESOLVED' for x in issues)==2
    assert any('SYS-1' in x['message'] and x['code']=='SUITE_BASELINE_COVERAGE_INCOMPLETE' for x in issues)


def test_required_any_uses_same_order_as_standalone_baseline_validation():
    baselines={'SSS':doc('SSS',artifact('requirement','SYS-1')),
               'SRS':doc('SRS',artifact('requirement','SW-1'))}
    assert selected_dependencies('STP',baselines)==['SRS']
    source=doc('STP',artifact('test-item','TEST-1',requirements=['SW-1']))
    assert reference_issues('STP',source,baselines)==[]
    assert any(x['code']=='SUITE_REFERENCE_UNRESOLVED' for x in reference_issues('STP',source,{'SSS':baselines['SSS']}))


def test_unregistered_artifact_kind_cannot_seed_baseline_index():
    source=doc('SDD',artifact('design-unit','DU-1',requirements=['BOGUS']))
    assert any(x['code']=='SUITE_REFERENCE_UNRESOLVED' for x in reference_issues('SDD',source,{
        'OCD':doc('OCD',artifact('requirement','BOGUS'))}))


@pytest.mark.parametrize('newline', ['\n','\r\n'])
@pytest.mark.parametrize('bom',['','\ufeff'])
def test_exact_utf8_bytes_survive_docx_roundtrip_and_volume_binding(tmp_path,monkeypatch,newline,bom):
    source=tmp_path/'source.md'
    template=Path(__file__).resolve().parents[1]/'examples/SRS.example.md'
    original=(bom+template.read_text(encoding='utf-8').replace('\n',newline)).encode('utf-8')
    source.write_bytes(original)
    parsed=parse_markdown(source)
    assert not parsed.parse_errors
    assert parsed.raw.encode('utf-8')==original
    word=tmp_path/'sample.docx'
    render_document(source,word,profile='review')
    result=import_word(word,tmp_path/'returned.md')
    assert result.exact_round_trip
    assert result.output.read_bytes()==original
    # Unit-test provenance independent of Office timing; integration runs separately.
    monkeypatch.setattr(volume,'rendered_page_metrics',lambda *a,**k:volume.RenderedPageMetrics(10,5,6,3000,0,0,0,0,100))
    report=volume.audit_rendered_volume(parsed,'SRS',word,tier='large')
    assert report.source_sha256==hashlib.sha256(original).hexdigest()==volume.sha256_file(source)


def test_fsync_file_uses_writable_nontruncating_handle(tmp_path,monkeypatch):
    path=tmp_path/'existing.bin';path.write_bytes(b'unchanged')
    real_open=Path.open
    observed=[]
    def open_spy(self,mode='r',*args,**kwargs):
        if self==path:observed.append(mode)
        return real_open(self,mode,*args,**kwargs)
    monkeypatch.setattr(Path,'open',open_spy)
    publication._fsync_file(path)
    assert observed==['r+b']
    assert path.read_bytes()==b'unchanged'


@pytest.mark.parametrize('mutation',['edit','delete'])
def test_source_register_change_during_render_preserves_previous_release(tmp_path,monkeypatch,mutation):
    source=tmp_path/'source.md';source.write_text('approved input',encoding='utf-8')
    register=tmp_path/'sources.md';register.write_text('SRC-1 original source',encoding='utf-8')
    word=tmp_path/'release.docx'
    destinations=[word,*[Path(str(word)+s) for s in ('.content.json','.audit.json','.volume.json')]]
    for p in destinations:p.write_bytes(b'previous-'+p.name.encode())
    previous={p:p.read_bytes() for p in destinations}
    payload={'passed':True,'provenance':{'source_sha256':volume.sha256_file(source),'baseline_sha256':{},
                                       'source_register_sha256':volume.sha256_file(register)}}
    monkeypatch.setattr(cli,'_audit_all',lambda a:(payload,'SRS','large',200,None))
    def render(source,target,**kw):
        target.write_bytes(b'new-docx')
        register.unlink() if mutation=='delete' else register.write_text('SRC-2 replaced source',encoding='utf-8')
    monkeypatch.setattr(cli,'render_document',render)
    monkeypatch.setattr(cli,'refresh_toc_cache',lambda p:None)
    ok=SimpleNamespace(passed=True,as_dict=lambda:{'passed':True})
    monkeypatch.setattr(cli,'audit_docx',lambda *a,**k:ok)
    monkeypatch.setattr(cli,'audit_rendered_volume',lambda *a,**k:ok)
    monkeypatch.setattr(cli,'publish_files',lambda *a,**kw:pytest.fail('changed register must never publish'))
    assert cli.main(['render',str(source),'--output',str(word),'--profile=release','--source-register',str(register)])!=0
    assert {p:p.read_bytes() for p in destinations}==previous


@pytest.mark.parametrize('value',['unknown', ['not','mapping'], 42, None])
def test_malformed_software_metadata_returns_failed_suite_json(tmp_path,value):
    manifest=initialize_suite(tmp_path/'suite')
    data=yaml.safe_load(manifest.read_text(encoding='utf-8'))
    source=manifest.parent/data['documents']['OCD']['markdown']
    original=source.read_text(encoding='utf-8');_,front,body=original.split('---',2)
    meta=yaml.safe_load(front);meta['software']=value
    source.write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True)+'---'+body,encoding='utf-8')
    report=tmp_path/'suite-report.json'
    assert cli.main(['audit-suite',str(manifest),'--profile','review','--json',str(report)])==5
    payload=json.loads(report.read_text(encoding='utf-8'))
    assert payload['passed'] is False
    assert any(x['code']=='SUITE_IDENTITY_MISMATCH' for x in payload['issues'])


@pytest.mark.parametrize('code',[x.code for x in iter_document_types()])
def test_all_packaged_outlines_keep_clause_numbers_and_match_profile(tmp_path,code):
    source=tmp_path/f'{code}.md'
    assert cli.main(['init','--type',code,'--output',str(source)])==0
    text=source.read_text(encoding='utf-8')
    # A clause must never receive a second numeric prefix.
    assert not re.search(r'^#{1,9}\s+\d+(?:\.\d+)*\s+\d+(?:\.[\dXxYy]+)+',text,re.M)
    report=audit_profile_document(source,document_type=code,audit_profile='draft')
    assert report.heading_coverage_percent==100, report.to_text()
    if code=='SRS':
        assert '### 3.2.X （软件能力）' in text
        assert '### 3.10.1 计算机硬件需求' in text
    if code=='SDD':assert '# 7 注释' in text


def test_explicit_numbers_advance_unnumbered_sibling_counters():
    text=render_skeleton(document_type=get_document_type('SRS'),outline=[
        Heading(1,'范围',0,'3'), Heading(2,'显式',0,'3.10'),
        Heading(2,'下一个',0),Heading(1,'下章',0)])
    assert '## 3.11 下一个' in text and '# 4 下章' in text
