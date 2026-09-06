"""The single public parser and protected publication path (no legacy dispatch)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Sequence
import yaml

from . import __version__
from .audit_docx import audit_docx
from .baselines import load_baselines, validate_baselines
from .finalize import FinalizeError, refresh_toc_cache
from .front_matter import FrontMatterError, load_payload, render_front_matter
from .import_word import ImportWordError, import_word
from .markdown_doc import extract_template_outline, parse_markdown, render_skeleton
from .profile_quality import ProfileQualityError, audit_markdown_with_profile, load_profile_mapping
from .profiles import ProfileError, heading_outline, profile_directory
from .publication import PublicationError, distinct_paths, publish_files, write_report
from .registry import get_document_type, iter_document_types, resolve_template
from .render import RenderError, render_document
from .suite import SuiteError, audit_suite_manifest, initialize_suite, manifest_artifact_paths
from .trust import approval_issues, fingerprint
from .volume import VolumeError, audit_rendered_volume, markdown_volume_issues, minimum_body_pages, resolve_tier, sha256_file, volume_policy


def build_parser():
    parser = argparse.ArgumentParser(prog='gjb438c', allow_abbrev=False)
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    def cmd(name, **kwargs):
        return sub.add_parser(name, allow_abbrev=False, **kwargs)
    def tier(p, default=None):
        p.add_argument('--tier', '--scale', dest='tier', default=default)
    def pages(p):
        p.add_argument('--min-body-pages', type=int)
    cmd('list')
    cmd('doctor')
    p = cmd('profile'); p.add_argument('--type', required=True); p.add_argument('--json', action='store_true')
    p = cmd('volume-policy'); p.add_argument('--type', required=True); tier(p, 'large'); p.add_argument('--json', action='store_true')
    p = cmd('init'); p.add_argument('--type', required=True); p.add_argument('--project'); p.add_argument('--template-root'); p.add_argument('--output', required=True)
    for name in ('audit', 'render'):
        p = cmd(name); p.add_argument('input'); p.add_argument('--type')
        p.add_argument('--profile', choices=['draft', 'review', 'release'], default='review')
        p.add_argument('--baseline-srs'); p.add_argument('--baseline-dir'); p.add_argument('--source-register'); tier(p); pages(p)
        if name == 'audit':
            p.add_argument('--json')
        else:
            p.add_argument('--output', required=True); p.add_argument('--front-template')
            p.add_argument('--docx-audit-json'); p.add_argument('--content-audit-json'); p.add_argument('--volume-json')
            p.add_argument('--refresh-toc', action='store_true')
    p = cmd('audit-volume'); p.add_argument('input'); p.add_argument('--source', required=True); p.add_argument('--type'); tier(p); pages(p); p.add_argument('--json')
    p = cmd('audit-docx'); p.add_argument('input'); p.add_argument('--profile', choices=['review', 'release'], default='review'); p.add_argument('--json')
    p = cmd('suite-init'); p.add_argument('--project'); p.add_argument('--output', required=True); tier(p, 'large'); pages(p); p.add_argument('--suite-id')
    p = cmd('audit-suite', aliases=['suite-audit']); p.add_argument('manifest'); p.add_argument('--profile', choices=['review', 'release'], default='release'); tier(p); p.add_argument('--write-volume-reports', action='store_true'); p.add_argument('--json')
    p = cmd('fingerprint'); p.add_argument('input')
    p = cmd('import-word'); p.add_argument('input'); p.add_argument('--output', required=True)
    p = cmd('refresh-toc'); p.add_argument('input'); p.add_argument('--output', required=True); p.add_argument('--audit-json')
    p = cmd('front-matter'); p.add_argument('--template', required=True); p.add_argument('--data', required=True); p.add_argument('--output', required=True); p.add_argument('--release', action='store_true')
    return parser


def _mapping(path):
    if not path:
        return {}
    value = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('project metadata must be a mapping')
    return value


def _audit_all(args):
    source = Path(args.input)
    document = parse_markdown(source)
    code = get_document_type(args.type or str(document.metadata.get('document', {}).get('type', ''))).code
    tier = resolve_tier(document, args.tier)
    quality = document.metadata.get('quality') or {}
    declared = quality.get('min_body_pages')
    floors = [minimum_body_pages(code, tier, v) for v in (declared, args.min_body_pages) if v is not None]
    floor = max([minimum_body_pages(code, tier), *floors])
    baselines = load_baselines(args.baseline_dir, args.baseline_srs)
    srs = baselines.get('SRS' if code == 'SDD' else 'SSS') if code in {'SDD', 'SSDD'} else None
    combined = audit_markdown_with_profile(source, profile=args.profile, document_type=code, baseline_srs=srs, tier=tier)
    issues = markdown_volume_issues(document, code, tier, args.profile, min_body_pages_override=floor)
    baseline_issues, hashes = validate_baselines(source, args.profile, baselines)
    issues.extend(baseline_issues)
    provenance = {'source_sha256': sha256_file(source), 'profile_sha256': sha256_file(profile_directory() / f'{code.lower()}.yaml'), 'baseline_sha256': hashes, 'tool_version': __version__}
    if args.source_register:
        register = Path(args.source_register)
        text = register.read_text(encoding='utf-8')
        provenance['source_register_sha256'] = sha256_file(register)
        for entry in document.metadata.get('sources', []):
            if isinstance(entry, dict) and str(entry.get('id', '')) not in text:
                issues.append({'severity': 'ERROR', 'code': 'SOURCE_REGISTER_MISMATCH', 'message': str(entry.get('id'))})
    payload = {'passed': combined.passed and not any(i['severity'] == 'ERROR' for i in issues), 'document_type': code, 'tier': tier, 'profile': args.profile,
               'approved_for_release': args.profile == 'release' and combined.passed and not any(i['severity'] == 'ERROR' for i in issues) and not approval_issues(document), 'content': combined.as_dict(), 'preflight': issues, 'provenance': provenance}
    return payload, code, tier, floor, srs


def _emit(payload, path=None, inputs=()):
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    if path:
        write_report(path, text, inputs=inputs)
    print(text)


def _render(args):
    target = Path(args.output).resolve()
    # All publication destinations are determined from argparse's FINAL values.
    # --profile=review --profile=release therefore cannot bypass this path.
    paths = {'docx': target, 'content': Path(args.content_audit_json or str(target)+'.content.json').resolve(),
             'docx_audit': Path(args.docx_audit_json or str(target)+'.audit.json').resolve()}
    if args.profile == 'release':
        paths['volume'] = Path(args.volume_json or str(target)+'.volume.json').resolve()
    elif args.volume_json:
        raise ValueError('--volume-json is only emitted by a release render; use audit-volume for candidates')
    inputs = [args.input]
    if args.front_template: inputs.append(args.front_template)
    if args.source_register: inputs.append(args.source_register)
    inputs.extend(load_baselines(args.baseline_dir, args.baseline_srs).values())
    distinct_paths([*paths.values(), *dict.fromkeys(map(str, inputs))])
    payload, code, tier, floor, srs = _audit_all(args)
    if not payload['passed']:
        _emit(payload)
        return 2
    with tempfile.TemporaryDirectory(prefix='gjb-build-') as folder:
        folder = Path(folder)
        draft = folder / 'document.docx'
        render_document(args.input, draft, profile=args.profile, baseline_srs=srs, front_template=args.front_template)
        if args.refresh_toc or args.profile == 'release':
            refresh_toc_cache(draft)
        docx_report = audit_docx(draft, profile='release' if args.profile == 'release' else 'review')
        if not docx_report.passed:
            _emit(docx_report.as_dict()); return 3
        docx_data = docx_report.as_dict()
        docx_data.update(path=str(target), source_sha256=payload['provenance']['source_sha256'], docx_sha256=sha256_file(draft), tool_version=__version__)
        reports = {'content': payload, 'docx_audit': docx_data}
        if args.profile == 'release':
            volume = audit_rendered_volume(args.input, code, draft, tier=tier, min_body_pages_override=floor)
            if not volume.passed:
                _emit(volume.as_dict()); return 4
            reports['volume'] = volume.as_dict()
        # Detect edits during a long Office render rather than certify mismatched
        # Markdown/evidence. Baseline files used by the audit are also bound.
        if sha256_file(args.input) != payload['provenance']['source_sha256']:
            raise PublicationError('source changed during render; no files published')
        current_bases = load_baselines(args.baseline_dir, args.baseline_srs)
        if any(k not in current_bases or sha256_file(current_bases[k]) != h for k, h in payload['provenance']['baseline_sha256'].items()):
            raise PublicationError('baseline changed during render; no files published')
        staged = {}
        for kind, data in reports.items():
            file = folder / f'{kind}.json'; file.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
            staged[paths[kind]] = file
        staged[target] = draft
        publish_files(staged, marker=target)
    _emit({'passed': True, 'profile': args.profile, 'files': {k: str(v) for k,v in paths.items()}, 'human_visual_review_required': True})
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == 'list':
            for item in iter_document_types(): print(f'{item.number:02d} {item.code} {item.chinese_name}')
        elif args.command == 'doctor':
            import shutil
            from .registry import default_front_matter_template
            codes=[item.code for item in iter_document_types()]
            for code in codes: load_profile_mapping(code)
            master=default_front_matter_template()
            _emit({'version':__version__,'python':sys.executable,'module':str(Path(__file__).resolve()),
                   'profile_root':str(profile_directory()),'document_types':codes,'bundled_master':str(master),
                   'authoring_ready':len(codes)==20 and master.is_file(),
                   'office_executable':shutil.which('libreoffice') or shutil.which('soffice'),
                   'note':'Office/fonts and human visual review are separately required for release; this is not project approval.'})
            return 0 if master.is_file() else 2
        elif args.command == 'profile': _emit(load_profile_mapping(args.type))
        elif args.command == 'volume-policy': _emit(volume_policy(args.type, args.tier))
        elif args.command == 'init':
            target = Path(args.output)
            if target.exists(): raise ValueError(f'refusing to overwrite existing Markdown: {target}')
            outline = extract_template_outline(resolve_template(args.type, Path(args.template_root))) if args.template_root else heading_outline(args.type)
            text = render_skeleton(document_type=get_document_type(args.type), outline=outline, project=_mapping(args.project))
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('x', encoding='utf-8') as stream: stream.write(text)
            print(target)
        elif args.command == 'audit':
            payload, *_ = _audit_all(args)
            _emit(payload, args.json, inputs=[args.input, *load_baselines(args.baseline_dir, args.baseline_srs).values(), *([args.source_register] if args.source_register else [])])
            return 0 if payload['passed'] else 2
        elif args.command == 'render': return _render(args)
        elif args.command == 'audit-volume':
            document = parse_markdown(args.source)
            code = get_document_type(args.type or str(document.metadata.get('document', {}).get('type',''))).code
            report = audit_rendered_volume(document, code, args.input, tier=args.tier, min_body_pages_override=args.min_body_pages)
            _emit(report.as_dict(), args.json, inputs=[args.input, args.source]); return 0 if report.passed else 4
        elif args.command == 'audit-docx':
            report = audit_docx(args.input, profile=args.profile)
            _emit(report.as_dict(), args.json, inputs=[args.input]); return 0 if report.passed else 3
        elif args.command == 'suite-init': print(initialize_suite(args.output, project=args.project, tier=args.tier, min_body_pages=args.min_body_pages, suite_id=args.suite_id))
        elif args.command in {'audit-suite','suite-audit'}:
            if args.json: distinct_paths([args.json, *manifest_artifact_paths(args.manifest)])
            report = audit_suite_manifest(args.manifest, audit_profile=args.profile, tier=args.tier, write_volume_reports=args.write_volume_reports)
            _emit(report.as_dict(), args.json, inputs=manifest_artifact_paths(args.manifest)); return 0 if report.passed else 5
        elif args.command == 'fingerprint': print(fingerprint(parse_markdown(args.input)))
        elif args.command == 'import-word':
            distinct_paths([args.input, args.output]); result=import_word(args.input, args.output); print(result.output); print('exact-round-trip' if result.exact_round_trip else result.warning)
        elif args.command == 'refresh-toc':
            distinct_paths([args.input, args.output, *([args.audit_json] if args.audit_json else [])])
            output=refresh_toc_cache(args.input, args.output)
            report=audit_docx(output, profile='release'); _emit(report.as_dict(), args.audit_json, inputs=[args.input,args.output]); return 0 if report.passed else 3
        elif args.command == 'front-matter':
            distinct_paths([args.template,args.data,args.output]); print(render_front_matter(args.template, load_payload(args.data), args.output, release=args.release))
        return 0
    except (OSError, ValueError, yaml.YAMLError, ProfileError, ProfileQualityError, PublicationError, SuiteError, VolumeError, RenderError, FrontMatterError, ImportWordError, FinalizeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
