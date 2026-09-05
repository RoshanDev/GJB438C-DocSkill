from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "skills" / "gjb438c-md-first" / "gjb438c_suite"
TESTS = ROOT / "skills" / "gjb438c-md-first" / "tests"

# A manifest override below the policy floor is already converted into a report
# issue during the first pass.  The later metadata-consistency pass must not
# raise the same VolumeError and abort the whole suite audit.
suite_path = PKG / "suite.py"
text = suite_path.read_text(encoding="utf-8")
old = '''            expected_floor = minimum_body_pages(
                code, normalized_tier, entry.get("min_body_pages") if isinstance(entry, dict) else None
            )
            if declared_floor is None or int(declared_floor) < expected_floor:
'''
new = '''            try:
                expected_floor = minimum_body_pages(
                    code,
                    normalized_tier,
                    entry.get("min_body_pages") if isinstance(entry, dict) else None,
                )
            except VolumeError:
                expected_floor = minimum_body_pages(code, normalized_tier)
            try:
                declared_floor_value = int(declared_floor) if declared_floor is not None else None
            except (TypeError, ValueError):
                declared_floor_value = None
            if declared_floor_value is None or declared_floor_value < expected_floor:
'''
if old not in text:
    raise SystemExit("suite metadata floor block not found")
text = text.replace(old, new)

# A full release audit must reject duplicate document entries under aliases and
# must not treat an unknown manifest key as a valid document baseline.
needle = '''        present = set(entries)
        for code in required:
'''
replacement = '''        present = {str(key).upper() for key in entries if str(key).upper() in all_codes}
        for code in required:
'''
if needle not in text:
    raise SystemExit("suite present-set block not found")
text = text.replace(needle, replacement)
suite_path.write_text(text, encoding="utf-8")

# A direct OOXML rewrite must preserve ZIP metadata and avoid duplicate names.
evidence_path = PKG / "evidence.py"
text = evidence_path.read_text(encoding="utf-8")
text = text.replace(
    'from zipfile import ZIP_DEFLATED, ZipFile',
    'from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo',
)
old = '''        with ZipFile(target, "r") as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        root = etree.fromstring(entries["word/document.xml"])
'''
new = '''        with ZipFile(target, "r") as archive:
            infos = archive.infolist()
            entries = {info.filename: archive.read(info.filename) for info in infos}
        root = etree.fromstring(entries["word/document.xml"])
'''
if old not in text:
    raise SystemExit("evidence read block not found")
text = text.replace(old, new)
old = '''            with ZipFile(temp, "w", compression=ZIP_DEFLATED) as archive:
                for name, payload in entries.items():
                    archive.writestr(name, payload)
'''
new = '''            with ZipFile(temp, "w", compression=ZIP_DEFLATED) as archive:
                written: set[str] = set()
                for info in infos:
                    name = info.filename
                    if name in written:
                        continue
                    written.add(name)
                    payload = entries[name]
                    cloned = ZipInfo(name, date_time=info.date_time)
                    cloned.compress_type = info.compress_type
                    cloned.comment = info.comment
                    cloned.extra = info.extra
                    cloned.create_system = info.create_system
                    cloned.external_attr = info.external_attr
                    cloned.internal_attr = info.internal_attr
                    archive.writestr(cloned, payload)
'''
if old not in text:
    raise SystemExit("evidence write block not found")
text = text.replace(old, new)
evidence_path.write_text(text, encoding="utf-8")

# The thin route skills must never advertise release rendering without the
# corresponding Markdown source and volume report.
for skill in sorted((ROOT / "skills").glob("gjb438c-*/SKILL.md")):
    if skill.parent.name == "gjb438c-md-first":
        continue
    raw = skill.read_text(encoding="utf-8")
    code = skill.parent.name.removeprefix("gjb438c-").upper()
    if "gjb438c audit-volume" not in raw:
        raise SystemExit(f"thin skill lacks audit-volume command: {skill}")
    if f"--source docs/{code}.md" not in raw:
        raise SystemExit(f"thin skill audit-volume lacks source binding: {skill}")
    if "--scale large" not in raw:
        raise SystemExit(f"thin skill lacks explicit scale: {skill}")

# Regression: a lower manifest floor must be reported, not raised; the suite
# audit must continue far enough to collect more than one issue.
test_path = TESTS / "test_post_review_followup.py"
test_path.write_text(
    '''from pathlib import Path\n\nimport yaml\n\nfrom gjb438c_suite.suite import audit_suite_manifest, initialize_suite\n\n\ndef test_lower_floor_is_reported_without_aborting_suite(tmp_path: Path):\n    manifest = initialize_suite(tmp_path / "suite", tier="large")\n    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))\n    data["documents"]["SSS"]["min_body_pages"] = 1\n    manifest.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")\n    report = audit_suite_manifest(manifest, audit_profile="review")\n    codes = {item.code for item in report.issues}\n    assert "SUITE_PAGE_OVERRIDE_INVALID" in codes\n    assert "SUITE_DOCX_MISSING" in codes\n\n\ndef test_unknown_manifest_document_is_rejected(tmp_path: Path):\n    manifest = initialize_suite(tmp_path / "suite", tier="large")\n    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))\n    data["documents"]["UNKNOWN"] = dict(data["documents"]["SRS"])\n    manifest.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")\n    report = audit_suite_manifest(manifest, audit_profile="review")\n    assert any(item.code == "SUITE_UNKNOWN_DOCUMENT_TYPE" for item in report.issues)\n''',
    encoding="utf-8",
)

print("post-review follow-up hardening applied")
