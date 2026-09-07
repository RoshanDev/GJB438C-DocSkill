from pathlib import Path
import yaml
import pytest
from gjb438c_suite.markdown_doc import parse_markdown,Artifact
from gjb438c_suite.profile_quality import audit_profile_document,resolve_document_tier
from gjb438c_suite.trust import approval_issues,fingerprint,tailoring_minimum
from gjb438c_suite.suite import audit_suite_manifest,initialize_suite,SuiteError


def document(tmp_path):
    path=tmp_path/'doc.md';path.write_text('---\ndocument:\n  type: SRS\n  status: draft\nquality:\n  tier: large\nsources:\n  - id: SRC-1\n---\n# 1 范围\n\nProject-specific requirements.\n')
    return parse_markdown(path)


def test_machine_pass_does_not_create_human_approval(tmp_path):
    d=document(tmp_path);assert approval_issues(d)
    d.metadata['document']['status']='approved'
    d.metadata['approval']={'reviewer':'Reviewer','approved_at':'2025-01-01'}
    d.metadata['approval']['content_sha256']=fingerprint(d)
    assert not approval_issues(d)
    d.body+='Edited after approval'
    assert any('fingerprint' in x for x in approval_issues(d))


def test_tailoring_requires_explicit_complete_approved_record(tmp_path):
    d=document(tmp_path)
    record={'id':'TAILOR-1','target_kind':'table','required_minimum':80,'accepted_minimum':42,
            'rationale':'Only confirmed schema entities are applicable','impact':'Full schema coverage retained',
            'source_refs':['SRC-1'],'status':'proposed','approved_by':'Reviewer','approved_at':'2025-01-01'}
    d.artifacts.append(Artifact('tailoring',record,1,'gjb-tailoring'))
    assert tailoring_minimum(d,'table',80)[0]==80
    record['status']='approved'
    assert tailoring_minimum(d,'table',80)==(42,[])
    record['source_refs']=['SRC-missing'];assert tailoring_minimum(d,'table',80)[0]==80


def test_large_tier_cannot_be_silently_downgraded(tmp_path):
    from gjb438c_suite.profile_quality import ProfileQualityError
    d=document(tmp_path)
    with pytest.raises(ProfileQualityError):resolve_document_tier(d,'prototype')


def test_suite_public_entry_is_importable_and_empty_suite_fails(tmp_path):
    # Regression for PR4's NameError: audit_suite is not an implementation.
    path=tmp_path/'suite.yaml';path.write_text('suite:\n  required_documents: []\ndocuments: {}\n')
    with pytest.raises(SuiteError):audit_suite_manifest(path,audit_profile='review')


def test_orphan_sps_manifest_entry_does_not_satisfy_svd(tmp_path,monkeypatch):
    import gjb438c_suite.suite as module
    from types import SimpleNamespace
    manifest=initialize_suite(tmp_path/'suite')
    data=yaml.safe_load(manifest.read_text())
    data['suite']['required_documents']=['SVD']
    # No real content audit here: isolate the baseline-candidate logic.
    monkeypatch.setattr(module,'audit_markdown_with_profile',lambda *a,**k:SimpleNamespace(passed=True,as_dict=lambda:{'generic':{'issues':[]},'profile':{'issues':[]}}))
    import gjb438c_suite.volume as volume
    monkeypatch.setattr(volume,'markdown_volume_issues',lambda *a,**k:[])
    manifest.write_text(yaml.safe_dump(data,allow_unicode=True))
    r=audit_suite_manifest(manifest,audit_profile='review')
    assert not r.passed
    assert any(x.code=='SUITE_REQUIRED_BASELINE_NOT_AUDITED' for x in r.issues)


def test_init_invalid_tier_or_floor_leaves_no_workspace(tmp_path):
    for kwargs in ({'tier':'invalid'},{'min_body_pages':-1}):
        target=tmp_path/'workspace'
        with pytest.raises(Exception):initialize_suite(target,**kwargs)
        assert not target.exists()
