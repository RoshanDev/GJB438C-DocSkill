from __future__ import annotations

from pathlib import Path
import re
import shutil
import textwrap

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "skills" / "gjb438c-md-first" / "gjb438c_suite"


def write(relative: str, content: str) -> None:
    path = ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")


write(
    "skills/gjb438c-md-first/gjb438c_suite/suite.py",
    r'''
    from __future__ import annotations

    from dataclasses import asdict, dataclass, field
    import json
    import math
    from pathlib import Path
    import re
    from typing import Any, Iterable

    import yaml

    from .audit_docx import audit_docx
    from .markdown_doc import MarkdownDocument, parse_markdown, render_skeleton
    from .profile_quality import (
        artifact_kind,
        artifact_mapping,
        audit_markdown_with_profile,
        document_type_from_metadata,
        load_profile_mapping,
        normalize_tier,
    )
    from .profiles import load_profile
    from .registry import get_document_type, iter_document_types
    from .volume import (
        VolumeError,
        audit_rendered_volume,
        minimum_body_pages,
        sha256_file,
        sha256_text,
    )


    class SuiteError(RuntimeError):
        pass


    @dataclass(frozen=True, slots=True)
    class SuiteIssue:
        severity: str
        code: str
        message: str
        document_type: str | None = None

        def as_dict(self) -> dict[str, Any]:
            return asdict(self)


    @dataclass(slots=True)
    class SuiteDocumentResult:
        document_type: str
        markdown: str
        docx: str
        volume_report: str
        body_pages: int = 0
        minimum_body_pages: int = 0
        passed: bool = False

        def as_dict(self) -> dict[str, Any]:
            return asdict(self)


    @dataclass(slots=True)
    class SuiteAuditReport:
        manifest: Path
        tier: str
        issues: list[SuiteIssue] = field(default_factory=list)
        documents: list[SuiteDocumentResult] = field(default_factory=list)
        total_body_pages: int = 0
        minimum_total_body_pages: int = 0

        @property
        def errors(self) -> list[SuiteIssue]:
            return [item for item in self.issues if item.severity == "ERROR"]

        @property
        def passed(self) -> bool:
            return not self.errors and bool(self.documents) and all(item.passed for item in self.documents)

        def as_dict(self) -> dict[str, Any]:
            return {
                "manifest": str(self.manifest),
                "tier": self.tier,
                "passed": self.passed,
                "summary": {
                    "errors": len(self.errors),
                    "warnings": sum(1 for item in self.issues if item.severity == "WARN"),
                    "documents": len(self.documents),
                    "total_body_pages": self.total_body_pages,
                    "minimum_total_body_pages": self.minimum_total_body_pages,
                },
                "documents": [item.as_dict() for item in self.documents],
                "issues": [item.as_dict() for item in self.issues],
            }

        def to_json(self) -> str:
            return json.dumps(self.as_dict(), ensure_ascii=False, indent=2)

        def to_text(self) -> str:
            state = "PASS" if self.passed else "FAIL"
            lines = [
                f"[{state}] suite {self.manifest} tier={self.tier}",
                f"documents={len(self.documents)} body_pages="
                f"{self.total_body_pages}/{self.minimum_total_body_pages} errors={len(self.errors)}",
            ]
            for item in self.documents:
                mark = "PASS" if item.passed else "FAIL"
                lines.append(
                    f"- {mark} {item.document_type}: body_pages="
                    f"{item.body_pages}/{item.minimum_body_pages}"
                )
            for issue in self.issues:
                scope = f" {issue.document_type}" if issue.document_type else ""
                lines.append(f"- {issue.severity} {issue.code}:{scope} {issue.message}")
            return "\n".join(lines)


    def _add(
        report: SuiteAuditReport,
        severity: str,
        code: str,
        message: str,
        document_type: str | None = None,
    ) -> None:
        report.issues.append(SuiteIssue(severity, code, message, document_type))


    def _load_yaml(path: Path) -> dict[str, Any]:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise SuiteError(f"无法读取 YAML {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise SuiteError(f"YAML 根节点必须是映射：{path}")
        return value


    def _project_mapping(value: str | Path | dict[str, Any] | None) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        return _load_yaml(Path(value))


    def _inject_front_matter(
        text: str,
        *,
        code: str,
        tier: str,
        min_body_pages: int,
        document_id: str,
    ) -> str:
        match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
        if match:
            metadata = yaml.safe_load(match.group(1)) or {}
            if not isinstance(metadata, dict):
                metadata = {}
            body = text[match.end():]
        else:
            metadata = {}
            body = text
        document = metadata.setdefault("document", {})
        if not isinstance(document, dict):
            document = metadata["document"] = {}
        document.update({"type": code, "id": document_id, "status": "draft"})
        quality = metadata.setdefault("quality", {})
        if not isinstance(quality, dict):
            quality = metadata["quality"] = {}
        quality.update(
            {
                "tier": tier,
                "min_body_pages": min_body_pages,
                "fixture": False,
                "review_state": "draft",
            }
        )
        return (
            "---\n"
            + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False).rstrip()
            + "\n---\n"
            + body.lstrip("\n")
        )


    def initialize_suite(
        output: str | Path,
        *,
        project: str | Path | dict[str, Any] | None = None,
        tier: str = "large",
        min_body_pages: int | None = None,
        suite_id: str | None = None,
    ) -> Path:
        target = Path(output).resolve()
        if target.exists() and any(target.iterdir()):
            raise SuiteError(f"输出目录非空，拒绝覆盖：{target}")
        target.mkdir(parents=True, exist_ok=True)
        docs_dir = target / "docs"
        dist_dir = target / "dist"
        reports_dir = target / "reports"
        for directory in (docs_dir, dist_dir, reports_dir):
            directory.mkdir(parents=True, exist_ok=True)
        project_data = _project_mapping(project)
        normalized_tier = normalize_tier(tier)
        identity = suite_id or str(
            project_data.get("project", {}).get("id")
            if isinstance(project_data.get("project"), dict)
            else ""
        ).strip() or "GJB438C-SUITE"
        entries: dict[str, Any] = {}
        required: list[str] = []
        for item in iter_document_types():
            code = item.code
            required.append(code)
            profile = load_profile(code)
            floor = minimum_body_pages(code, normalized_tier)
            if min_body_pages is not None:
                floor = max(floor, int(min_body_pages))
            markdown_name = f"[{item.number:02d}][{code}] {item.chinese_name}.md"
            docx_name = f"[{item.number:02d}][{code}] {item.chinese_name}.docx"
            report_name = f"[{item.number:02d}][{code}] volume.json"
            markdown_path = docs_dir / markdown_name
            skeleton = render_skeleton(
                document_type=get_document_type(code),
                outline=profile.outline,
                project=project_data,
            )
            markdown_path.write_text(
                _inject_front_matter(
                    skeleton,
                    code=code,
                    tier=normalized_tier,
                    min_body_pages=floor,
                    document_id=f"{identity}-{code}",
                ),
                encoding="utf-8",
            )
            entries[code] = {
                "markdown": markdown_path.relative_to(target).as_posix(),
                "docx": (dist_dir / docx_name).relative_to(target).as_posix(),
                "volume_report": (reports_dir / report_name).relative_to(target).as_posix(),
                "min_body_pages": floor,
            }
        manifest = {
            "schema_version": 1,
            "suite": {
                "id": identity,
                "tier": normalized_tier,
                "status": "draft",
                "required_documents": required,
                "min_body_pages_each": min_body_pages,
                "tailoring": {},
                "page_floor_is_project_policy": True,
            },
            "documents": entries,
        }
        manifest_path = target / "suite.yaml"
        manifest_path.write_text(
            yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return manifest_path


    def _resolve(base: Path, value: Any, label: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise SuiteError(f"{label} 缺少路径")
        path = Path(value.strip())
        return path if path.is_absolute() else (base / path).resolve()


    def _doc_status(document: MarkdownDocument) -> str:
        value = document.metadata.get("document")
        if isinstance(value, dict):
            return str(value.get("status", "")).strip().lower()
        return ""


    def _artifact_index(documents: dict[str, MarkdownDocument]) -> dict[str, set[str]]:
        index: dict[str, set[str]] = {}
        for document in documents.values():
            for artifact in getattr(document, "artifacts", ()) or ():
                kind = artifact_kind(artifact)
                payload = artifact_mapping(artifact)
                artifact_id = str(payload.get("id", "")).strip()
                if kind and artifact_id:
                    index.setdefault(kind, set()).add(artifact_id)
        return index


    def _reference_values(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in re.split(r"[,;；\s]+", value) if item.strip()]
        if isinstance(value, (list, tuple, set)):
            result: list[str] = []
            for item in value:
                result.extend(_reference_values(item))
            return result
        return [str(value)]


    def _cross_reference_issues(
        report: SuiteAuditReport,
        documents: dict[str, MarkdownDocument],
    ) -> None:
        index = _artifact_index(documents)
        for code, document in documents.items():
            profile = load_profile_mapping(code)
            contracts = {
                str(item.get("kind", "")): item
                for item in profile.get("artifact_contracts", [])
                if isinstance(item, dict)
            }
            for artifact in getattr(document, "artifacts", ()) or ():
                kind = artifact_kind(artifact)
                contract = contracts.get(kind, {})
                references = contract.get("references", {})
                if not isinstance(references, dict):
                    continue
                payload = artifact_mapping(artifact)
                artifact_id = str(payload.get("id", "")).strip() or "<无ID>"
                for field_name, target in references.items():
                    if not isinstance(target, str) or not target.startswith("baseline:"):
                        continue
                    target_kind = target.split(":", 1)[1].strip()
                    for reference in _reference_values(payload.get(field_name)):
                        if reference not in index.get(target_kind, set()):
                            _add(
                                report,
                                "ERROR",
                                "SUITE_REFERENCE_UNRESOLVED",
                                f"{artifact_id}.{field_name} 引用 {reference}，但套件中不存在 gjb-{target_kind}",
                                code,
                            )


    def audit_suite_manifest(
        manifest: str | Path,
        *,
        audit_profile: str = "release",
        tier: str | None = None,
        write_volume_reports: bool = False,
    ) -> SuiteAuditReport:
        manifest_path = Path(manifest).resolve()
        data = _load_yaml(manifest_path)
        suite = data.get("suite")
        entries = data.get("documents")
        if not isinstance(suite, dict) or not isinstance(entries, dict):
            raise SuiteError("manifest 必须包含 suite 和 documents 映射")
        normalized_tier = normalize_tier(tier or suite.get("tier") or "large")
        report = SuiteAuditReport(manifest_path, normalized_tier)
        base = manifest_path.parent
        all_codes = [item.code for item in iter_document_types()]
        required = [str(item).upper() for item in suite.get("required_documents", all_codes)]
        tailoring = suite.get("tailoring", {})
        if not isinstance(tailoring, dict):
            tailoring = {}
        for code in all_codes:
            if code in required:
                continue
            reason = tailoring.get(code)
            if not isinstance(reason, str) or len(reason.strip()) < 12:
                _add(
                    report,
                    "ERROR",
                    "SUITE_TAILORING_RATIONALE_REQUIRED",
                    "省略文档必须给出不少于 12 个字符的项目特定剪裁理由",
                    code,
                )
        for code in required:
            if code not in entries:
                _add(report, "ERROR", "SUITE_DOCUMENT_MISSING", "manifest 缺少文档条目", code)
        documents: dict[str, MarkdownDocument] = {}
        total_floor = 0
        for code in required:
            entry = entries.get(code)
            if not isinstance(entry, dict):
                continue
            try:
                markdown_path = _resolve(base, entry.get("markdown"), f"{code}.markdown")
                docx_path = _resolve(base, entry.get("docx"), f"{code}.docx")
                volume_path = _resolve(base, entry.get("volume_report"), f"{code}.volume_report")
            except SuiteError as exc:
                _add(report, "ERROR", "SUITE_PATH_INVALID", str(exc), code)
                continue
            floor = minimum_body_pages(code, normalized_tier, entry.get("min_body_pages"))
            total_floor += floor
            result = SuiteDocumentResult(
                document_type=code,
                markdown=str(markdown_path),
                docx=str(docx_path),
                volume_report=str(volume_path),
                minimum_body_pages=floor,
            )
            report.documents.append(result)
            if not markdown_path.is_file():
                _add(report, "ERROR", "SUITE_MARKDOWN_MISSING", str(markdown_path), code)
                continue
            document = parse_markdown(markdown_path)
            documents[code] = document
            declared = document_type_from_metadata(document)
            if declared != code:
                _add(report, "ERROR", "SUITE_TYPE_MISMATCH", f"Markdown 声明 {declared!r}", code)
            if audit_profile == "release" and _doc_status(document) not in {
                "approved", "released", "baseline", "reviewed", "已批准", "已发布", "已基线",
            }:
                _add(
                    report,
                    "ERROR",
                    "SUITE_DOCUMENT_NOT_APPROVED",
                    f"document.status={_doc_status(document)!r}，正式套件只接受已审核/批准/基线状态",
                    code,
                )
            baseline_srs: Path | None = None
            if code == "SDD" and isinstance(entries.get("SRS"), dict):
                baseline_srs = _resolve(base, entries["SRS"].get("markdown"), "SRS.markdown")
            if code == "SSDD" and isinstance(entries.get("SSS"), dict):
                baseline_srs = _resolve(base, entries["SSS"].get("markdown"), "SSS.markdown")
            combined = audit_markdown_with_profile(
                markdown_path,
                profile=audit_profile,
                document_type=code,
                baseline_srs=baseline_srs,
                tier=normalized_tier,
            )
            if not combined.passed:
                _add(report, "ERROR", "SUITE_MARKDOWN_AUDIT_FAILED", combined.to_text(), code)
            if not docx_path.is_file():
                _add(report, "ERROR", "SUITE_DOCX_MISSING", str(docx_path), code)
                continue
            docx_report = audit_docx(docx_path, profile="release" if audit_profile == "release" else "review")
            if not docx_report.passed:
                _add(report, "ERROR", "SUITE_DOCX_AUDIT_FAILED", docx_report.to_text(), code)
            try:
                volume = audit_rendered_volume(
                    document,
                    code,
                    docx_path,
                    tier=normalized_tier,
                    min_body_pages_override=floor,
                )
            except (VolumeError, OSError) as exc:
                _add(report, "ERROR", "SUITE_VOLUME_AUDIT_FAILED", str(exc), code)
                continue
            result.body_pages = volume.body_pages
            report.total_body_pages += volume.body_pages
            if not volume.passed:
                _add(report, "ERROR", "SUITE_VOLUME_AUDIT_FAILED", volume.to_text(), code)
            if write_volume_reports:
                volume_path.parent.mkdir(parents=True, exist_ok=True)
                volume_path.write_text(volume.to_json(), encoding="utf-8")
            if not volume_path.is_file():
                _add(report, "ERROR", "SUITE_VOLUME_REPORT_MISSING", str(volume_path), code)
            else:
                try:
                    persisted = json.loads(volume_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    _add(report, "ERROR", "SUITE_VOLUME_REPORT_INVALID", str(exc), code)
                else:
                    if persisted.get("source_sha256") != sha256_text(document.raw):
                        _add(report, "ERROR", "SUITE_SOURCE_HASH_MISMATCH", "体量报告与 Markdown 不一致", code)
                    if persisted.get("docx_sha256") != sha256_file(docx_path):
                        _add(report, "ERROR", "SUITE_DOCX_HASH_MISMATCH", "体量报告与 DOCX 不一致", code)
            result.passed = combined.passed and docx_report.passed and volume.passed

        present = set(entries)
        for code in required:
            mapping = load_profile_mapping(code)
            baselines = mapping.get("baselines", {})
            if not isinstance(baselines, dict):
                continue
            for required_code in baselines.get("required", []) or []:
                required_code = str(required_code).upper()
                if required_code not in present:
                    _add(
                        report,
                        "ERROR",
                        "SUITE_REQUIRED_BASELINE_MISSING",
                        f"缺少必选基线 {required_code}",
                        code,
                    )
            required_any = [str(item).upper() for item in baselines.get("required_any", []) or []]
            if required_any and not (set(required_any) & present):
                _add(
                    report,
                    "ERROR",
                    "SUITE_ANY_BASELINE_MISSING",
                    f"至少需要一个基线：{', '.join(required_any)}",
                    code,
                )
        _cross_reference_issues(report, documents)
        computed_floor = total_floor
        requested_total = suite.get("min_portfolio_body_pages")
        if requested_total is not None and int(requested_total) < computed_floor:
            _add(
                report,
                "ERROR",
                "SUITE_PORTFOLIO_FLOOR_CANNOT_LOWER",
                f"min_portfolio_body_pages 只能提高下限；逐文档下限合计为 {computed_floor}",
            )
        report.minimum_total_body_pages = max(computed_floor, int(requested_total or 0))
        if report.total_body_pages < report.minimum_total_body_pages:
            _add(
                report,
                "ERROR",
                "SUITE_PORTFOLIO_BODY_PAGES_LOW",
                f"套件正文总页数 {report.total_body_pages} 低于 {report.minimum_total_body_pages}",
            )
        return report
    ''',
)

write(
    "skills/gjb438c-md-first/gjb438c_suite/suite_cli.py",
    r'''
    from __future__ import annotations

    import sys

    from .cli import main


    def suite_main() -> int:
        return main(["suite-init", *sys.argv[1:]])


    if __name__ == "__main__":
        raise SystemExit(suite_main())
    ''',
)

write(
    "skills/gjb438c-md-first/gjb438c_suite/cli.py",
    r'''
    from __future__ import annotations

    import argparse
    import json
    import os
    from pathlib import Path
    import sys
    import tempfile
    from typing import Any, Sequence

    import yaml

    from .audit_docx import audit_docx
    from .evidence import append_evidence_appendix
    from .finalize import FinalizeError, refresh_toc_cache
    from .front_matter import FrontMatterError, load_payload, render_front_matter
    from .import_word import ImportWordError, import_word
    from .markdown_doc import extract_template_outline, parse_markdown, render_skeleton
    from .profile_quality import (
        ProfileQualityError,
        audit_markdown_with_profile,
        document_type_from_metadata,
        load_profile_mapping,
        normalize_tier,
    )
    from .profiles import load_profile
    from .registry import get_document_type, iter_document_types, resolve_template
    from .render import RenderError, render_document
    from .suite import SuiteError, audit_suite_manifest, initialize_suite
    from .volume import (
        VolumeError,
        audit_rendered_volume,
        markdown_volume_issues,
        minimum_body_pages,
        resolve_tier,
        volume_policy,
    )


    def _load_mapping(path: str | Path | None) -> dict[str, Any]:
        if not path:
            return {}
        source = Path(path)
        text = source.read_text(encoding="utf-8")
        value = json.loads(text) if source.suffix.lower() == ".json" else yaml.safe_load(text)
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError(f"{source} 必须是 JSON/YAML 对象")
        return value


    def _write_text(text: str, output: str | None) -> None:
        if output:
            target = Path(output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        print(text)


    def _tier_option(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--scale",
            "--tier",
            dest="tier",
            help="项目规模：prototype、standard、large、critical（兼容 small/medium/very-large 别名）",
        )


    def _min_pages_option(parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--min-body-pages",
            "--min-pages",
            dest="min_body_pages",
            type=int,
            help="只允许提高 Profile 正文页下限，不能降低",
        )


    def build_parser() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="gjb438c", description="GJB 438C Markdown-first 文档工程")
        sub = parser.add_subparsers(dest="command", required=True)
        sub.add_parser("list", help="列出 20 类 GJB 438C 文档")

        profile = sub.add_parser("profile", help="查看某类文档的完整 Profile 合同")
        profile.add_argument("--type", required=True)
        profile.add_argument("--json", action="store_true")

        init = sub.add_parser("init", help="用内置 Profile 创建 Markdown 骨架；模板根目录仅用于重新抽取")
        init.add_argument("--type", required=True)
        init.add_argument("--template-root")
        init.add_argument("--project", help="项目元数据 JSON/YAML")
        init.add_argument("--output", required=True)

        audit = sub.add_parser("audit", help="审核 Markdown、Profile 字段合同和体量前置条件")
        audit.add_argument("input")
        audit.add_argument("--profile", choices=["draft", "review", "release"], default="review")
        audit.add_argument("--type")
        audit.add_argument("--baseline-srs")
        audit.add_argument("--json")
        _tier_option(audit)
        _min_pages_option(audit)

        render = sub.add_parser("render", help="原子生成 DOCX；release 必须通过真实渲染体量门禁")
        render.add_argument("input")
        render.add_argument("--output", required=True)
        render.add_argument("--profile", choices=["draft", "review", "release"], default="review")
        render.add_argument("--type")
        render.add_argument("--baseline-srs")
        render.add_argument("--front-template")
        render.add_argument("--docx-audit-json")
        render.add_argument("--volume-json")
        render.add_argument("--body-start-page", type=int)
        render.add_argument("--refresh-toc", action="store_true")
        _tier_option(render)
        _min_pages_option(render)

        volume = sub.add_parser("audit-volume", help="按真实 Office 渲染结果审核正文页数、薄页和重复页")
        volume.add_argument("input", help="DOCX 文件")
        volume.add_argument("--source", required=True, help="对应的 Markdown 内容基线")
        volume.add_argument("--type")
        volume.add_argument("--body-start-page", type=int)
        volume.add_argument("--json")
        _tier_option(volume)
        _min_pages_option(volume)

        policy = sub.add_parser("volume-policy", help="查看某文档类型和项目规模的体量合同")
        policy.add_argument("--type", required=True)
        policy.add_argument("--scale", "--tier", dest="tier", required=True)
        policy.add_argument("--json", action="store_true")

        suite_init = sub.add_parser("suite-init", help="一次创建 20 类 Markdown 草稿及套件清单")
        suite_init.add_argument("--project")
        suite_init.add_argument("--output", required=True)
        suite_init.add_argument("--scale", "--tier", dest="tier", default="large")
        suite_init.add_argument("--min-body-pages", type=int)
        suite_init.add_argument("--suite-id")

        suite_audit = sub.add_parser("audit-suite", help="审核 20 类文档、基线、追踪、Word 和体量报告")
        suite_audit.add_argument("manifest")
        suite_audit.add_argument("--profile", choices=["review", "release"], default="release")
        suite_audit.add_argument("--scale", "--tier", dest="tier")
        suite_audit.add_argument("--write-volume-reports", action="store_true")
        suite_audit.add_argument("--json")

        finalize = sub.add_parser("refresh-toc", help="刷新 DOCX 的可见目录缓存")
        finalize.add_argument("input")
        finalize.add_argument("--output")
        finalize.add_argument("--audit-json")

        imp = sub.add_parser("import-word", help="将生成后的 Word 回流为候选 Markdown")
        imp.add_argument("input")
        imp.add_argument("--output", required=True)

        docx_audit = sub.add_parser("audit-docx", help="审核 DOCX 字体、字号、字段和结构")
        docx_audit.add_argument("input")
        docx_audit.add_argument("--profile", choices=["review", "release"], default="review")
        docx_audit.add_argument("--json")

        front = sub.add_parser("front-matter", help="单独填充统一前三页")
        front.add_argument("--template", required=True)
        front.add_argument("--data", required=True)
        front.add_argument("--output", required=True)
        front.add_argument("--release", action="store_true")
        return parser


    def _code(source: str | Path, explicit: str | None = None) -> str:
        if explicit:
            return explicit.strip().upper()
        detected = document_type_from_metadata(parse_markdown(source))
        if not detected:
            raise ProfileQualityError("无法从 Markdown front matter 确定 document.type；请传 --type")
        return detected


    def _audit_all(args) -> tuple[Any, list[dict[str, Any]], str, str]:
        code = _code(args.input, args.type)
        document = parse_markdown(args.input)
        tier = resolve_tier(document, args.tier)
        combined = audit_markdown_with_profile(
            args.input,
            profile=args.profile,
            document_type=code,
            baseline_srs=args.baseline_srs,
            tier=tier,
        )
        volume_issues = markdown_volume_issues(
            document,
            code,
            tier,
            args.profile,
            min_body_pages_override=args.min_body_pages,
        )
        return combined, volume_issues, code, tier


    def _audit_payload(combined, volume_issues, code: str, tier: str) -> dict[str, Any]:
        return {
            "passed": combined.passed and not any(item["severity"] == "ERROR" for item in volume_issues),
            "document_type": code,
            "tier": tier,
            "content": combined.as_dict(),
            "volume_preflight": volume_issues,
        }


    def main(argv: Sequence[str] | None = None) -> int:
        parser = build_parser()
        args = parser.parse_args(argv)
        try:
            if args.command == "list":
                for item in iter_document_types():
                    print(f"{item.number:02d} {item.code:<4} {item.chinese_name} {item.clause} 附录{item.appendix}")
                return 0

            if args.command == "profile":
                value = load_profile_mapping(args.type)
                print(json.dumps(value, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(value, allow_unicode=True, sort_keys=False))
                return 0

            if args.command == "init":
                item = get_document_type(args.type)
                if args.template_root:
                    template = resolve_template(args.type, Path(args.template_root))
                    outline = extract_template_outline(template)
                else:
                    outline = load_profile(args.type).outline
                project = _load_mapping(args.project)
                output = Path(args.output)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(render_skeleton(document_type=item, outline=outline, project=project), encoding="utf-8")
                print(output)
                return 0

            if args.command == "audit":
                combined, volume_issues, code, tier = _audit_all(args)
                payload = _audit_payload(combined, volume_issues, code, tier)
                text = json.dumps(payload, ensure_ascii=False, indent=2) if args.json else (
                    combined.to_text()
                    + "\n"
                    + "\n".join(
                        f"- {item['severity']} {item['code']}: {item['message']}" for item in volume_issues
                    )
                )
                _write_text(text, args.json if args.json else None)
                return 0 if payload["passed"] else 2

            if args.command == "render":
                combined, volume_issues, code, tier = _audit_all(args)
                errors = [item for item in volume_issues if item["severity"] == "ERROR"]
                if not combined.passed or errors:
                    print(combined.to_text(), file=sys.stderr)
                    for item in volume_issues:
                        print(f"{item['severity']} {item['code']}: {item['message']}", file=sys.stderr)
                    return 2
                target = Path(args.output).resolve()
                target.parent.mkdir(parents=True, exist_ok=True)
                temp = target.parent / f".{target.stem}.building-{os.getpid()}.docx"
                try:
                    result = render_document(
                        args.input,
                        temp,
                        profile=args.profile,
                        baseline_srs=args.baseline_srs,
                        front_template=args.front_template,
                    )
                    append_evidence_appendix(result.output, args.input)
                    if args.refresh_toc:
                        refresh_toc_cache(result.output)
                    docx_report = audit_docx(
                        result.output,
                        profile="release" if args.profile == "release" else "review",
                    )
                    if args.docx_audit_json:
                        Path(args.docx_audit_json).write_text(docx_report.to_json(), encoding="utf-8")
                    if not docx_report.passed:
                        print(docx_report.to_text(), file=sys.stderr)
                        return 3
                    volume_report = None
                    if args.profile == "release":
                        volume_report = audit_rendered_volume(
                            args.input,
                            code,
                            result.output,
                            tier=tier,
                            min_body_pages_override=args.min_body_pages,
                            body_start_page=args.body_start_page,
                        )
                        if args.volume_json:
                            volume_target = Path(args.volume_json)
                            volume_target.parent.mkdir(parents=True, exist_ok=True)
                            volume_target.write_text(volume_report.to_json(), encoding="utf-8")
                        if not volume_report.passed:
                            print(volume_report.to_text(), file=sys.stderr)
                            return 4
                    os.replace(result.output, target)
                    print(target)
                    print(docx_report.to_text())
                    if volume_report:
                        print(volume_report.to_text())
                    return 0
                finally:
                    if temp.exists():
                        temp.unlink()

            if args.command == "audit-volume":
                code = _code(args.source, args.type)
                document = parse_markdown(args.source)
                tier = resolve_tier(document, args.tier)
                result = audit_rendered_volume(
                    document,
                    code,
                    args.input,
                    tier=tier,
                    min_body_pages_override=args.min_body_pages,
                    body_start_page=args.body_start_page,
                )
                _write_text(result.to_json() if args.json else result.to_text(), args.json)
                return 0 if result.passed else 4

            if args.command == "volume-policy":
                value = volume_policy(args.type, args.tier)
                print(json.dumps(value, ensure_ascii=False, indent=2) if args.json else yaml.safe_dump(value, allow_unicode=True, sort_keys=False))
                return 0

            if args.command == "suite-init":
                path = initialize_suite(
                    args.output,
                    project=args.project,
                    tier=args.tier,
                    min_body_pages=args.min_body_pages,
                    suite_id=args.suite_id,
                )
                print(path)
                return 0

            if args.command == "audit-suite":
                report = audit_suite_manifest(
                    args.manifest,
                    audit_profile=args.profile,
                    tier=args.tier,
                    write_volume_reports=args.write_volume_reports,
                )
                _write_text(report.to_json() if args.json else report.to_text(), args.json)
                return 0 if report.passed else 5

            if args.command == "refresh-toc":
                output = refresh_toc_cache(args.input, args.output)
                report = audit_docx(output, profile="release")
                if args.audit_json:
                    Path(args.audit_json).write_text(report.to_json(), encoding="utf-8")
                print(output)
                print(report.to_text())
                return 0 if report.passed else 3

            if args.command == "import-word":
                result = import_word(args.input, args.output)
                print(result.output)
                print("exact-round-trip" if result.exact_round_trip else result.warning)
                return 0

            if args.command == "audit-docx":
                report = audit_docx(args.input, profile=args.profile)
                _write_text(report.to_json() if args.json else report.to_text(), args.json)
                return 0 if report.passed else 3

            if args.command == "front-matter":
                payload = load_payload(args.data)
                output = render_front_matter(args.template, payload, args.output, release=args.release)
                print(output)
                return 0

            parser.error(f"未知命令：{args.command}")
            return 2
        except (
            ValueError,
            FileNotFoundError,
            FrontMatterError,
            RenderError,
            ImportWordError,
            FinalizeError,
            ProfileQualityError,
            VolumeError,
            SuiteError,
        ) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2


    if __name__ == "__main__":
        raise SystemExit(main())
    ''',
)

# Explicit fixture releases are allowed to exercise formatting/round-trip in CI,
# but production documents cannot use prototype. For fixtures, do not impose the
# project-size page floor.
volume_path = PKG / "volume.py"
volume_text = volume_path.read_text(encoding="utf-8")
needle = """        floor = minimum_body_pages(document_type, normalized, min_body_pages_override)\n        base_pages = max(1, int(policy.get(\"minimum_pages\", 1)))\n"""
replacement = """        floor = minimum_body_pages(document_type, normalized, min_body_pages_override)\n        if normalized == \"prototype\" and is_fixture(document) and min_body_pages_override is None:\n            floor = 1\n        base_pages = max(1, int(policy.get(\"minimum_pages\", 1)))\n"""
if needle not in volume_text:
    raise SystemExit("volume fixture insertion point not found")
volume_path.write_text(volume_text.replace(needle, replacement), encoding="utf-8")

# Fix cached mutable profile returns. Cache the raw object internally and always
# deep-copy at the public boundary.
profiles_path = PKG / "profiles.py"
profiles_text = profiles_path.read_text(encoding="utf-8")
if "def _load_profile_cached(" not in profiles_text:
    lines = profiles_text.splitlines()
    def_index = next((i for i, line in enumerate(lines) if line.startswith("def load_profile(")), None)
    if def_index is None:
        raise SystemExit("profiles.py load_profile not found")
    decorator_start = def_index
    while decorator_start > 0 and lines[decorator_start - 1].startswith("@"):
        decorator_start -= 1
    if not any("lru_cache" in line for line in lines[decorator_start:def_index]):
        lines.insert(decorator_start, "@lru_cache(maxsize=None)")
        def_index += 1
    lines[def_index] = lines[def_index].replace("def load_profile(", "def _load_profile_cached(", 1)
    end = def_index + 1
    while end < len(lines):
        line = lines[end]
        if line and not line.startswith((" ", "\t")) and (line.startswith("def ") or line.startswith("@")):
            break
        end += 1
    wrapper = [
        "",
        "def load_profile(code: str):",
        "    \"\"\"Return an isolated copy so callers cannot weaken later audits.\"\"\"",
        "    return deepcopy(_load_profile_cached(str(code).strip().upper()))",
        "",
    ]
    lines[end:end] = wrapper
    profiles_text = "\n".join(lines) + "\n"
if "from copy import deepcopy" not in profiles_text:
    profiles_text = profiles_text.replace("from __future__ import annotations\n", "from __future__ import annotations\n\nfrom copy import deepcopy\n", 1)
profiles_path.write_text(profiles_text, encoding="utf-8")

# Package dependencies and executable alias.
pyproject = ROOT / "skills" / "gjb438c-md-first" / "pyproject.toml"
pyproject_text = pyproject.read_text(encoding="utf-8")
if "pypdf" not in pyproject_text.lower():
    match = re.search(r"dependencies\s*=\s*\[", pyproject_text)
    if not match:
        raise SystemExit("pyproject dependencies array not found")
    pos = match.end()
    pyproject_text = pyproject_text[:pos] + '\n  "pypdf>=5.0",' + pyproject_text[pos:]
if "gjb438c-suite" not in pyproject_text:
    marker = "[project.scripts]"
    if marker not in pyproject_text:
        pyproject_text += "\n[project.scripts]\n"
    pyproject_text = pyproject_text.replace(
        marker,
        marker + '\ngjb438c-suite = "gjb438c_suite.suite_cli:suite_main"',
        1,
    )
pyproject.write_text(pyproject_text, encoding="utf-8")

# Update all thin route skills to commands that really exist and bind the source
# Markdown when auditing Word volume.
for skill in sorted((ROOT / "skills").glob("gjb438c-*/SKILL.md")):
    if skill.parent.name == "gjb438c-md-first":
        continue
    text = skill.read_text(encoding="utf-8")
    text = text.replace("--tier ", "--scale ")
    code = skill.parent.name.removeprefix("gjb438c-").upper()
    text = re.sub(
        rf"gjb438c audit-volume\s+dist/{re.escape(code)}\.docx[^\n]*",
        f"gjb438c audit-volume dist/{code}.docx --source docs/{code}.md --type {code} --scale large --json reports/{code}.volume.json",
        text,
    )
    render_line = rf"(gjb438c render\s+docs/{re.escape(code)}\.md[^\n]*)"
    match = re.search(render_line, text)
    if match and "--scale" not in match.group(1):
        updated = match.group(1) + f" --scale large --volume-json reports/{code}.volume.json"
        text = text[:match.start()] + updated + text[match.end():]
    skill.write_text(text, encoding="utf-8")

core_skill = ROOT / "skills" / "gjb438c-md-first" / "SKILL.md"
core_text = core_skill.read_text(encoding="utf-8")
addition = r'''

## 强制发布链路

正式发布不得绕过以下命令：

```bash
gjb438c audit docs/SRS.md --profile release --scale large
gjb438c render docs/SRS.md --output dist/SRS.docx --profile release \
  --scale large --min-body-pages 300 --refresh-toc \
  --volume-json reports/SRS.volume.json
gjb438c audit-volume dist/SRS.docx --source docs/SRS.md \
  --type SRS --scale large --min-body-pages 300 \
  --json reports/SRS.volume.json
gjb438c audit-suite suite.yaml --profile release --write-volume-reports
```

`--min-body-pages` 是项目验收策略，只能提高 Profile 下限，不能降低。正文页数不包含首页、签字页、修改页和目录。页数本身不能通过发布门禁；还会检查可见正文密度、薄页、重复页、重复长段落、Profile 条目数量、来源和跨文档追踪。

使用 `gjb438c suite-init --output <dir> --scale large --min-body-pages 300` 可创建 20 类文档草稿和 `suite.yaml`，但初始化结果仍是 draft，不得冒充完成的正式交付物。
'''
if "## 强制发布链路" not in core_text:
    core_skill.write_text(core_text.rstrip() + addition, encoding="utf-8")

# Remove leaked bootstrap/self-modifying integration files. The active repair
# workflow removes itself only after verification.
for relative in (
    ".bootstrap-v03",
    ".github/workflows/analyze-template-pages.yml",
    ".github/workflows/apply-v03-profiles.yml",
    ".github/workflows/export-gjb438c-feature-source.yml",
    ".github/workflows/export-review-source.yml",
    ".github/workflows/finalize-v03.yml",
    "tools/apply_v03_profiles.py",
):
    path = ROOT / relative
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()

print("runtime core B written")
