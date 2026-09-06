"""Validate selected Markdown baselines in this run; filenames are not approval."""
from __future__ import annotations
from pathlib import Path
from typing import Mapping

from .markdown_doc import parse_markdown
from .profile_quality import audit_markdown_with_profile, load_profile_mapping
from .registry import get_document_type
from .trust import approval_issues
from .references import reference_issues
from .volume import markdown_volume_issues, resolve_tier, sha256_file


def load_baselines(directory: str | Path | None, explicit_srs: str | Path | None = None) -> dict[str, Path]:
    paths = {}
    if directory:
        root = Path(directory)
        if not root.is_dir():
            raise ValueError(f"baseline directory does not exist: {root}")
        for path in sorted(root.glob('*.md')):
            document = parse_markdown(path)
            code = get_document_type(str(document.metadata.get('document', {}).get('type', ''))).code
            if code in paths:
                raise ValueError(f"ambiguous baseline {code}: {paths[code]} and {path}")
            paths[code] = path
    if explicit_srs:
        path = Path(explicit_srs)
        document = parse_markdown(path)
        code = get_document_type(str(document.metadata.get('document', {}).get('type', ''))).code
        if code not in {'SRS', 'SSS'}:
            raise ValueError('--baseline-srs must identify SRS or SSS')
        if code in paths and paths[code].resolve() != path.resolve():
            raise ValueError(f'conflicting baseline paths for {code}')
        paths[code] = path
    return paths


def validate_baselines(source: str | Path, phase: str, paths: Mapping[str, Path]) -> tuple[list[dict], dict[str, str]]:
    root = parse_markdown(source)
    root_code = get_document_type(str(root.metadata.get('document', {}).get('type', ''))).code
    identity = root.metadata.get('software', {}).get('identifier')
    valid: dict[str, str] = {}
    invalid: dict[str, str] = {}

    def validate(code: str, stack: tuple[str, ...]) -> bool:
        code = get_document_type(code).code
        if code in valid:
            return True
        if code in invalid:
            return False
        if code in stack:
            invalid[code] = 'dependency cycle: ' + ' -> '.join((*stack, code))
            return False
        path = paths.get(code)
        if path is None or not path.is_file():
            invalid[code] = 'baseline not selected or not readable'
            return False
        baseline = parse_markdown(path)
        if baseline.metadata.get('software', {}).get('identifier') != identity:
            invalid[code] = 'baseline belongs to a different software identifier'
            return False
        if phase == 'release' and approval_issues(baseline):
            invalid[code] = '; '.join(approval_issues(baseline))
            return False
        srs = paths.get('SRS' if code == 'SDD' else 'SSS') if code in {'SDD', 'SSDD'} else None
        report = audit_markdown_with_profile(path, profile=phase, document_type=code, baseline_srs=srs)
        preflight = markdown_volume_issues(baseline, code, resolve_tier(baseline), phase)
        if not report.passed or any(x['severity'] == 'ERROR' for x in preflight):
            invalid[code] = 'baseline failed current content/profile/volume-preflight audit'
            return False
        errors = requirements(code, (*stack, code))
        if errors:
            invalid[code] = '; '.join(errors)
            return False
        scoped = {key: parse_markdown(paths[key]) for key in valid}
        ref_errors = reference_issues(code, baseline, scoped)
        if ref_errors:
            invalid[code] = '; '.join(x['message'] for x in ref_errors)
            return False
        valid[code] = sha256_file(path)
        return True

    def requirements(code: str, stack: tuple[str, ...]) -> list[str]:
        spec = load_profile_mapping(code).get('baselines', {})
        errors = []
        for dep in spec.get('required', []):
            if not validate(dep, stack):
                errors.append(f'{dep}: {invalid.get(dep, "invalid baseline")}')
        choices = spec.get('required_any', [])
        if choices and not any(validate(dep, stack) for dep in choices):
            errors.append('no successfully audited baseline among ' + ', '.join(choices))
        return errors

    messages = requirements(root_code, (root_code,))
    severity = 'WARN' if phase == 'draft' else 'ERROR'
    issues = [{'severity': severity, 'code': 'BASELINE_NOT_AUDITED', 'message': m} for m in messages]
    issues.extend(reference_issues(root_code, root, {code: parse_markdown(paths[code]) for code in valid}, severity=severity))
    return issues, valid
