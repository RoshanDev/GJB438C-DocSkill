from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class DocumentType:
    number: int
    code: str
    chinese_name: str
    clause: str
    appendix: str
    template_filename: str
    required_artifacts: tuple[str, ...]
    aliases: tuple[str, ...] = ()


# `required_artifacts` is this repository's engineering quality floor. It is
# intentionally not presented as verbatim standard text. The exact chapter
# outline is extracted from the selected GJB 438C template at `init` time.
_ROWS = [
    (1, "SDP", "软件开发计划", "5.1", "A", "[01][SDP] 软件开发计划-438C-2021.docx",
     ("scope", "lifecycle", "organization", "schedule", "resource", "method", "risk", "assurance")),
    (2, "SIP", "软件安装计划", "5.2", "B", "[02][SIP] 软件安装计划-438C-2021.docx",
     ("environment", "prerequisite", "installation", "configuration", "rollback", "verification", "security")),
    (3, "STrP", "软件移交计划", "5.3", "C", "[03][STrP] 软件移交计划-438C-2021.docx",
     ("deliverable", "responsibility", "transition", "training", "migration", "acceptance", "rollback")),
    (4, "STP", "软件测试计划", "5.4", "D", "[04][STP] 软件测试计划-438C-2021.docx",
     ("test-scope", "test-strategy", "test-environment", "test-data", "schedule", "entry-exit", "defect", "traceability")),
    (5, "OCD", "运行方案说明", "5.5", "E", "[05][OCD] 运行方案说明-438C-2021.docx",
     ("mission", "user", "scenario", "environment", "mode-state", "external-interface", "constraint")),
    (6, "SSS", "系统/子系统规格说明", "5.6", "F", "[06][SSS] 系统-子系统规格说明-438C-2021.docx",
     ("requirement", "interface", "performance", "safety-security", "environment", "verification", "traceability")),
    (7, "IRS", "接口需求规格说明", "5.7", "G", "[07][IRS] 接口需求规格说明-438C-2021.docx",
     ("interface-requirement", "message", "protocol", "timing", "error", "security", "verification", "traceability")),
    (8, "SSDD", "系统/子系统设计说明", "5.8", "H", "[08][SSDD] 系统-子系统设计说明-438C-2021.docx",
     ("decision", "architecture", "design-unit", "interface", "data", "scenario", "deployment", "security", "verification", "traceability")),
    (9, "IDD", "接口设计说明", "5.9", "I", "[09][IDD] 接口设计说明-438C-2021.docx",
     ("interface", "message", "protocol", "state", "timing", "error", "security", "compatibility", "verification")),
    (10, "SRS", "软件需求规格说明", "5.10", "J", "[10][SRS] 软件需求规格说明-438C-2021.docx",
     ("requirement", "traceability"), ("软件需求规格说明书",)),
    (11, "SDD", "软件设计说明", "5.11", "K", "[11][SDD] 软件设计说明-438C-2021.docx",
     ("decision", "architecture", "design-unit", "interface", "data", "scenario", "deployment", "security", "verification", "traceability"),
     ("软件设计说明书", "概要设计", "详细设计")),
    (12, "DBDD", "数据库设计说明", "5.12", "L", "[12][DBDD] 数据库设计说明-438C-2021.docx",
     ("data-model", "table", "constraint", "index", "transaction", "retention", "backup-recovery", "security", "migration", "traceability")),
    (13, "STD", "软件测试说明", "5.13", "M", "[13][STD] 软件测试说明-438C-2021.docx",
     ("test-case", "setup", "procedure", "test-data", "expected-result", "cleanup", "traceability")),
    (14, "STR", "软件测试报告", "5.14", "N", "[14][STR] 软件测试报告-438C-2021.docx",
     ("test-result", "deviation", "defect", "coverage", "conclusion", "traceability")),
    (15, "SPS", "软件产品规格说明", "5.15", "O", "[15][SPS] 软件产品规格说明-438C-2021.docx",
     ("product", "component", "build", "dependency", "configuration", "installation", "operation", "limitation", "integrity")),
    (16, "SVD", "软件版本说明", "5.16", "P", "[16][SVD] 软件版本说明-438C-2021.docx",
     ("version", "change", "build", "compatibility", "installation", "known-issue", "verification", "checksum")),
    (17, "SUM", "软件用户手册", "5.17", "Q", "[17][SUM] 软件用户手册-438C-2021.docx",
     ("audience", "task", "procedure", "interface", "error", "troubleshooting", "security", "reference")),
    (18, "CPM", "计算机编程手册", "5.18", "R", "[18][CPM] 计算机编程手册-438C-2021.docx",
     ("architecture", "code-organization", "build", "coding-standard", "api", "data", "error", "concurrency", "testing", "maintenance")),
    (19, "FSM", "固件保障手册", "5.19", "S", "[19][FSM] 固件保障手册-438C-2021.docx",
     ("firmware-item", "hardware-interface", "programming", "update", "rollback", "diagnostic", "security", "recovery")),
    (20, "SDSR", "软件研制总结报告", "5.20", "T", "[20][SDSR] 软件研制总结报告-438C-2021.docx",
     ("scope", "result", "metric", "issue", "change", "lesson", "deliverable", "conclusion")),
]

DOCUMENT_TYPES: dict[str, DocumentType] = {
    row[1]: DocumentType(*row) for row in _ROWS
}
_ALIAS_MAP: dict[str, str] = {}
for item in DOCUMENT_TYPES.values():
    for key in (item.code, item.chinese_name, *item.aliases):
        _ALIAS_MAP[key.strip().lower()] = item.code


def get_document_type(value: str) -> DocumentType:
    key = value.strip().lower()
    code = _ALIAS_MAP.get(key, value.strip().upper())
    try:
        return DOCUMENT_TYPES[code]
    except KeyError as exc:
        supported = ", ".join(DOCUMENT_TYPES)
        raise ValueError(f"未知 GJB 438C 文档类型 {value!r}；支持：{supported}") from exc


def iter_document_types() -> Iterable[DocumentType]:
    return sorted(DOCUMENT_TYPES.values(), key=lambda item: item.number)


def repository_root() -> Path:
    # .../skills/gjb438c-md-first/gjb438c_suite/registry.py -> repository root
    return Path(__file__).resolve().parents[3]


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_template_root() -> Path:
    return repository_root() / "GJB438C全套模版" / "438C-2021全套模板"


def default_front_matter_template() -> Path:
    return skill_root() / "templates" / "front-matter" / "standard-front-matter.docx"


def resolve_template(document_type: str | DocumentType, template_root: Path | None = None) -> Path:
    item = get_document_type(document_type) if isinstance(document_type, str) else document_type
    root = Path(template_root) if template_root else default_template_root()
    path = root / item.template_filename
    if not path.is_file():
        raise FileNotFoundError(
            f"未找到 {item.code} 模板：{path}。请保留仓库中的 20 份模板，或用 --template-root 指定目录。"
        )
    return path
