from __future__ import annotations

"""Repository-owned document profiles.

These profiles are an engineering quality policy built on top of the GJB 438C
chapter structures.  They are deliberately not represented as verbatim clauses
of the standard.  The generator combines this catalog with the checked-in DOCX
outline sources and writes self-contained runtime profile YAML files.
"""

from copy import deepcopy
from typing import Any

TIERS = ("prototype", "standard", "large", "critical")

DEFAULT_FIELDS = (
    "id",
    "title",
    "description",
    "source_refs",
)

ARTIFACT_FIELDS: dict[str, tuple[str, ...]] = {
    "requirement": (
        "id", "statement", "rationale", "source", "priority", "verification", "acceptance",
    ),
    "traceability": ("id", "source_refs", "requirements", "forward_targets"),
    "decision": (
        "id", "context", "options", "decision", "rationale", "consequences", "status", "source_refs",
    ),
    "architecture": (
        "id", "components", "connectors", "deployment", "failure_domains", "source_refs",
    ),
    "design-unit": (
        "id", "requirements", "responsibility", "behavior", "interfaces", "data", "states",
        "errors", "concurrency", "security", "deployment", "verification", "source_refs",
    ),
    "interface": (
        "id", "provider", "consumer", "protocol", "input", "output", "timing", "errors",
        "security", "compatibility", "source_refs",
    ),
    "interface-requirement": (
        "id", "interface", "statement", "source", "priority", "data", "timing", "errors",
        "security", "verification", "acceptance", "source_refs",
    ),
    "message": (
        "id", "interface", "direction", "trigger", "fields", "encoding", "size", "timing",
        "validation", "error_response", "source_refs",
    ),
    "data": (
        "id", "owner", "schema", "constraints", "transaction", "retention", "security",
        "recovery", "source_refs",
    ),
    "data-model": (
        "id", "scope", "entities", "relationships", "ownership", "consistency", "source_refs",
    ),
    "table": (
        "id", "name", "purpose", "owner", "columns", "primary_key", "foreign_keys",
        "constraints", "indexes", "volume", "retention", "backup_recovery", "security", "source_refs",
    ),
    "scenario": (
        "id", "requirements", "trigger", "actors", "preconditions", "steps", "failures",
        "postconditions", "observability", "source_refs",
    ),
    "deployment": (
        "id", "nodes", "placement", "resources", "network", "storage", "upgrade", "rollback",
        "source_refs",
    ),
    "security": (
        "id", "assets", "threats", "controls", "audit", "residual_risk", "source_refs",
    ),
    "verification": (
        "id", "target", "method", "environment", "criteria", "evidence", "source_refs",
    ),
    "schedule": (
        "id", "activity", "start", "end", "dependencies", "owner", "deliverables",
        "entry_criteria", "exit_criteria", "source_refs",
    ),
    "risk": (
        "id", "description", "cause", "probability", "impact", "owner", "mitigation",
        "trigger", "contingency", "status", "source_refs",
    ),
    "activity-plan": (
        "id", "activity", "inputs", "tasks", "methods", "outputs", "roles", "schedule",
        "quality_controls", "completion_criteria", "source_refs",
    ),
    "site": (
        "id", "name", "environment", "contacts", "facilities", "security_constraints", "source_refs",
    ),
    "installation-task": (
        "id", "site", "component", "prerequisites", "procedure", "configuration", "verification",
        "rollback", "owner", "duration", "source_refs",
    ),
    "deliverable": (
        "id", "name", "version", "form", "owner", "recipient", "acceptance", "checksum", "source_refs",
    ),
    "transition-task": (
        "id", "task", "inputs", "procedure", "outputs", "owner", "recipient", "schedule",
        "acceptance", "rollback", "source_refs",
    ),
    "test-item": (
        "id", "requirements", "objective", "level", "method", "environment", "data",
        "entry_criteria", "exit_criteria", "responsible", "schedule", "source_refs",
    ),
    "test-environment": (
        "id", "hardware", "software", "network", "data", "tools", "configuration",
        "isolation", "reset", "source_refs",
    ),
    "test-case": (
        "id", "requirements", "objective", "preconditions", "environment", "test_data", "steps",
        "expected_results", "pass_criteria", "cleanup", "automation", "source_refs",
    ),
    "test-execution": (
        "id", "test_case", "build", "environment", "executor", "date", "status", "actual_results",
        "evidence", "defects", "deviations", "source_refs",
    ),
    "defect": (
        "id", "summary", "severity", "priority", "found_in", "requirements", "status", "resolution",
        "verification", "residual_risk", "source_refs",
    ),
    "coverage": (
        "id", "scope", "metric", "planned", "achieved", "uncovered_items", "rationale", "source_refs",
    ),
    "operational-scenario": (
        "id", "users", "mission", "trigger", "environment", "preconditions", "workflow", "alternatives",
        "degraded_modes", "postconditions", "source_refs",
    ),
    "mode-state": (
        "id", "states", "initial_state", "transitions", "guards", "actions", "failure_states", "source_refs",
    ),
    "release": (
        "id", "version", "baseline", "build", "date", "contents", "changes", "compatibility",
        "installation", "known_issues", "checksums", "source_refs",
    ),
    "product-item": (
        "id", "name", "version", "type", "path", "purpose", "dependencies", "configuration",
        "integrity", "source_refs",
    ),
    "procedure": (
        "id", "goal", "actor", "preconditions", "steps", "expected_result", "errors", "recovery",
        "security", "source_refs",
    ),
    "api": (
        "id", "name", "purpose", "signature", "parameters", "returns", "errors", "thread_safety",
        "examples", "source_refs",
    ),
    "firmware-item": (
        "id", "name", "version", "target_hardware", "memory_map", "interfaces", "programming",
        "update", "rollback", "diagnostics", "integrity", "source_refs",
    ),
    "metric": (
        "id", "name", "definition", "source", "target", "actual", "trend", "interpretation", "source_refs",
    ),
    "issue": (
        "id", "description", "impact", "root_cause", "resolution", "verification", "status", "source_refs",
    ),
    "quality-control": (
        "id", "work_product", "method", "criteria", "findings", "disposition", "evidence", "source_refs",
    ),
    "assurance": (
        "id", "activity", "independence", "method", "criteria", "findings", "closure", "evidence", "source_refs",
    ),
}


def _contract(kind: str, *, minimum: tuple[int, int, int, int] = (1, 1, 1, 1),
              fields: tuple[str, ...] | None = None,
              references: dict[str, str] | None = None,
              coverage: bool = False) -> dict[str, Any]:
    return {
        "kind": kind,
        "required_fields": list(fields or ARTIFACT_FIELDS.get(kind, DEFAULT_FIELDS)),
        "minimum": dict(zip(TIERS, minimum, strict=True)),
        "references": references or {},
        "coverage": coverage,
    }


# Page floors are repository quality policy, not a claim that GJB 438C itself
# prescribes a page count.  Prototype is for smoke tests and must not pass a
# production release gate.  Standard/large/critical are intentionally strict.
PAGE_FLOORS: dict[str, tuple[int, int, int, int]] = {
    "SDP": (10, 40, 80, 120), "SIP": (8, 25, 40, 60), "STrP": (8, 25, 40, 60),
    "STP": (12, 50, 100, 160), "OCD": (10, 40, 80, 120), "SSS": (15, 100, 180, 280),
    "IRS": (12, 60, 120, 180), "SSDD": (15, 120, 220, 350), "IDD": (12, 80, 150, 220),
    "SRS": (15, 100, 200, 320), "SDD": (15, 150, 250, 400), "DBDD": (12, 80, 150, 240),
    "STD": (15, 100, 220, 350), "STR": (12, 80, 150, 240), "SPS": (10, 50, 100, 160),
    "SVD": (8, 30, 50, 80), "SUM": (12, 80, 180, 300), "CPM": (12, 80, 150, 240),
    "FSM": (10, 50, 100, 160), "SDSR": (10, 60, 120, 200),
}

PURPOSES = {
    "SDP": "策划并控制软件开发全过程、方法、资源、进度、风险和保证活动。",
    "SIP": "策划用户现场的软件安装、转换、培训、验证和回退。",
    "STrP": "策划向保障机构移交软件产品、资源、知识和责任。",
    "STP": "策划 CSCI 或系统/子系统合格性测试的范围、环境、方法、进度和追踪。",
    "OCD": "描述用户需要、运行环境、使用方式、任务场景和与现有系统的关系。",
    "SSS": "定义系统/子系统需求、外部接口、质量特性和鉴定检验方法。",
    "IRS": "定义实体之间一个或多个接口的可验证需求。",
    "SSDD": "描述系统/子系统级设计决策、体系结构、执行方案和分配关系。",
    "IDD": "描述接口设计、消息、协议、状态、时序、错误和兼容性。",
    "SRS": "定义 CSCI 的完整、无歧义、可验证和可追踪需求。",
    "SDD": "描述 CSCI 的设计决策、体系结构、设计单元、接口、数据和执行行为。",
    "DBDD": "描述数据库逻辑/物理模型、表、约束、索引、事务、安全和恢复。",
    "STD": "规定每个测试用例的设置、数据、步骤、检查点、判据和追踪。",
    "STR": "记录测试执行事实、结果、偏差、缺陷、覆盖和结论。",
    "SPS": "精确定义可交付软件产品、组成、构建、配置、安装、运行和完整性。",
    "SVD": "说明一个发布版本的基线、变更、构建、兼容性、安装和已知问题。",
    "SUM": "面向用户说明任务、操作、界面、错误处理、故障排查和安全注意事项。",
    "CPM": "面向维护开发人员说明代码组织、构建、编码约定、API、并发和测试。",
    "FSM": "说明固件目标、硬件接口、烧写、升级、回退、诊断和恢复。",
    "SDSR": "总结研制结果、度量、重大问题、质量控制、保证活动和经验教训。",
}

BASELINES: dict[str, dict[str, list[str]]] = {
    "SDP": {"required": [], "optional": ["OCD", "SSS", "SRS"]},
    "SIP": {"required": ["SPS", "SVD"], "optional": ["SUM", "DBDD"]},
    "STrP": {"required": ["SPS", "SVD"], "optional": ["SUM", "CPM", "FSM"]},
    "STP": {"required_any": ["SRS", "SSS"], "optional": ["IRS"]},
    "OCD": {"required": [], "optional": ["SSS"]},
    "SSS": {"required": ["OCD"], "optional": ["IRS"]},
    "IRS": {"required_any": ["SSS", "SRS"], "optional": []},
    "SSDD": {"required": ["SSS"], "optional": ["IRS", "IDD", "DBDD"]},
    "IDD": {"required": ["IRS"], "optional": ["SSDD", "SDD"]},
    "SRS": {"required_any": ["SSS", "OCD"], "optional": ["IRS"]},
    "SDD": {"required": ["SRS"], "optional": ["IRS", "IDD", "DBDD"]},
    "DBDD": {"required_any": ["SDD", "SSDD"], "optional": ["SRS", "SSS", "IDD"]},
    "STD": {"required": ["STP"], "required_any": ["SRS", "SSS"], "optional": ["IRS"]},
    "STR": {"required": ["STD"], "optional": ["STP", "SRS", "SSS"]},
    "SPS": {"required_any": ["SDD", "SSDD"], "optional": ["DBDD", "IDD"]},
    "SVD": {"required": ["SPS"], "optional": ["STR"]},
    "SUM": {"required_any": ["SRS", "SVD"], "optional": ["SIP"]},
    "CPM": {"required_any": ["SDD", "SSDD"], "optional": ["IDD", "DBDD"]},
    "FSM": {"required_any": ["SPS", "SDD"], "optional": ["IDD"]},
    "SDSR": {"required": ["SDP", "STR", "SVD"], "optional": ["SRS", "SDD", "STP"]},
}

SOURCE_MATERIALS = {
    "SDP": ["合同/技术协议", "生存周期模型", "WBS 与里程碑", "组织和资源计划", "风险清单", "保证与配置管理制度"],
    "SIP": ["产品规格与版本说明", "现场调查记录", "部署拓扑", "安装脚本与配置", "培训计划", "回退方案"],
    "STrP": ["交付清单", "配置基线", "保障资源清单", "培训资料", "知识转移计划", "验收准则"],
    "STP": ["需求基线", "接口需求", "测试策略", "测试环境清单", "测试资源和进度", "准入退出准则"],
    "OCD": ["用户访谈", "任务流程", "运行规程", "现有系统资料", "典型/异常/降级场景", "环境约束"],
    "SSS": ["任务需求", "总体技术要求", "OCD", "系统边界与外部接口", "质量特性指标", "鉴定检验方法"],
    "IRS": ["接口控制资料", "上下游实体规格", "协议标准", "数据字典", "时序与错误场景", "安全约束"],
    "SSDD": ["SSS 基线", "架构决策记录", "系统分解", "硬软件分配", "接口与数据设计", "部署与执行模型"],
    "IDD": ["IRS 基线", "协议/消息定义", "API/总线规范", "状态机与时序", "错误码", "兼容性策略"],
    "SRS": ["SSS/OCD/合同需求", "用户场景", "接口需求", "性能与资源预算", "质量特性", "验收与验证依据"],
    "SDD": ["已审核 SRS", "架构决策记录", "代码/模型", "接口与数据模型", "部署拓扑", "异常与并发设计"],
    "DBDD": ["SDD/SSDD", "数据字典", "ER 模型", "DDL", "容量与性能预算", "备份恢复与迁移方案"],
    "STD": ["STP", "需求基线", "接口需求", "环境配置", "测试数据", "自动化脚本与判据"],
    "STR": ["STD", "执行日志", "测试证据", "缺陷记录", "覆盖率报告", "偏差审批与复测记录"],
    "SPS": ["构建产物", "SBOM/依赖", "配置基线", "安装与运行信息", "完整性校验", "限制条件"],
    "SVD": ["SPS", "变更记录", "构建流水线", "兼容性矩阵", "安装升级说明", "已知问题与校验值"],
    "SUM": ["需求和版本说明", "交互原型/截图", "用户任务", "错误与告警", "故障排查", "安全使用要求"],
    "CPM": ["SDD/代码仓库", "构建脚本", "编码规范", "API 文档", "数据模型", "测试和维护指南"],
    "FSM": ["固件映像", "硬件规格", "存储布局", "烧写/升级工具", "诊断记录", "恢复与完整性方案"],
    "SDSR": ["SDP 与历次修订", "需求/设计/测试基线", "度量数据", "重大问题闭环", "质量保证记录", "交付与版本清单"],
}

CONTRACTS: dict[str, list[dict[str, Any]]] = {
    "SDP": [
        _contract("activity-plan", minimum=(1, 12, 30, 50)),
        _contract("schedule", minimum=(1, 10, 25, 40)),
        _contract("risk", minimum=(1, 8, 20, 35)),
        _contract("assurance", minimum=(1, 4, 8, 12)),
        _contract("traceability"),
    ],
    "SIP": [
        _contract("site", minimum=(1, 1, 3, 5)),
        _contract("installation-task", minimum=(2, 15, 35, 60)),
        _contract("procedure", minimum=(1, 8, 20, 35)),
        _contract("verification", minimum=(1, 8, 20, 35)),
        _contract("risk", minimum=(1, 5, 12, 20)),
        _contract("traceability"),
    ],
    "STrP": [
        _contract("deliverable", minimum=(2, 15, 35, 60)),
        _contract("transition-task", minimum=(1, 12, 30, 50)),
        _contract("procedure", minimum=(1, 8, 20, 30)),
        _contract("risk", minimum=(1, 5, 12, 20)),
        _contract("traceability"),
    ],
    "STP": [
        _contract("test-item", minimum=(2, 20, 60, 100), references={"requirements": "baseline:requirement"}, coverage=True),
        _contract("test-environment", minimum=(1, 2, 4, 6)),
        _contract("schedule", minimum=(1, 8, 20, 35)),
        _contract("risk", minimum=(1, 6, 15, 25)),
        _contract("traceability"),
    ],
    "OCD": [
        _contract("operational-scenario", minimum=(2, 15, 35, 60)),
        _contract("mode-state", minimum=(1, 2, 4, 6)),
        _contract("interface", minimum=(1, 8, 20, 35)),
        _contract("risk", minimum=(1, 5, 12, 20)),
        _contract("traceability"),
    ],
    "SSS": [
        _contract("requirement", minimum=(5, 100, 220, 400), coverage=True),
        _contract("interface-requirement", minimum=(1, 20, 60, 100)),
        _contract("verification", minimum=(2, 40, 100, 180)),
        _contract("traceability"),
    ],
    "IRS": [
        _contract("interface-requirement", minimum=(3, 40, 100, 180), coverage=True),
        _contract("message", minimum=(2, 30, 80, 140)),
        _contract("mode-state", minimum=(1, 3, 8, 15)),
        _contract("verification", minimum=(2, 20, 60, 100)),
        _contract("traceability"),
    ],
    "SSDD": [
        _contract("decision", minimum=(1, 8, 20, 35)),
        _contract("architecture", minimum=(1, 2, 4, 6)),
        _contract("design-unit", minimum=(2, 25, 60, 100), references={"requirements": "baseline:requirement"}, coverage=True),
        _contract("interface", minimum=(2, 20, 60, 100)),
        _contract("data", minimum=(1, 15, 40, 70)),
        _contract("scenario", minimum=(1, 20, 60, 100), references={"requirements": "baseline:requirement"}),
        _contract("deployment", minimum=(1, 2, 4, 6)),
        _contract("security", minimum=(1, 5, 12, 20)),
        _contract("verification", minimum=(1, 20, 60, 100)),
        _contract("traceability"),
    ],
    "IDD": [
        _contract("interface", minimum=(2, 20, 60, 100), coverage=True),
        _contract("message", minimum=(2, 40, 120, 200)),
        _contract("mode-state", minimum=(1, 4, 10, 18)),
        _contract("security", minimum=(1, 4, 10, 18)),
        _contract("verification", minimum=(1, 20, 60, 100)),
        _contract("traceability"),
    ],
    "SRS": [
        _contract("requirement", minimum=(5, 100, 250, 450), coverage=True),
        _contract("interface-requirement", minimum=(1, 20, 60, 100)),
        _contract("verification", minimum=(2, 40, 120, 200)),
        _contract("traceability"),
    ],
    "SDD": [
        _contract("decision", minimum=(1, 10, 25, 40)),
        _contract("architecture", minimum=(1, 2, 4, 6)),
        _contract("design-unit", minimum=(2, 30, 80, 130), references={"requirements": "baseline:requirement"}, coverage=True),
        _contract("interface", minimum=(2, 25, 80, 130)),
        _contract("data", minimum=(1, 20, 60, 100)),
        _contract("scenario", minimum=(1, 30, 90, 150), references={"requirements": "baseline:requirement"}),
        _contract("deployment", minimum=(1, 2, 4, 6)),
        _contract("security", minimum=(1, 6, 15, 25)),
        _contract("verification", minimum=(1, 30, 80, 130)),
        _contract("traceability"),
    ],
    "DBDD": [
        _contract("data-model", minimum=(1, 2, 4, 6)),
        _contract("table", minimum=(2, 30, 80, 140)),
        _contract("decision", minimum=(1, 6, 15, 25)),
        _contract("procedure", minimum=(1, 10, 30, 50)),
        _contract("security", minimum=(1, 5, 12, 20)),
        _contract("verification", minimum=(1, 10, 30, 50)),
        _contract("traceability"),
    ],
    "STD": [
        _contract("test-environment", minimum=(1, 2, 4, 6)),
        _contract("test-case", minimum=(3, 100, 300, 500), references={"requirements": "baseline:requirement"}, coverage=True),
        _contract("procedure", minimum=(1, 20, 60, 100)),
        _contract("traceability"),
    ],
    "STR": [
        _contract("test-execution", minimum=(3, 100, 300, 500), references={"test_case": "baseline:test-case"}, coverage=True),
        _contract("defect", minimum=(0, 1, 1, 1)),
        _contract("coverage", minimum=(1, 4, 8, 12)),
        _contract("issue", minimum=(0, 1, 1, 1)),
        _contract("traceability"),
    ],
    "SPS": [
        _contract("product-item", minimum=(2, 20, 60, 100)),
        _contract("procedure", minimum=(1, 10, 30, 50)),
        _contract("interface", minimum=(1, 10, 30, 50)),
        _contract("security", minimum=(1, 4, 10, 18)),
        _contract("verification", minimum=(1, 10, 30, 50)),
        _contract("traceability"),
    ],
    "SVD": [
        _contract("release", minimum=(1, 1, 1, 1)),
        _contract("deliverable", minimum=(2, 20, 60, 100)),
        _contract("issue", minimum=(0, 1, 1, 1)),
        _contract("verification", minimum=(1, 8, 20, 35)),
        _contract("traceability"),
    ],
    "SUM": [
        _contract("procedure", minimum=(2, 50, 140, 240)),
        _contract("operational-scenario", minimum=(1, 20, 60, 100)),
        _contract("interface", minimum=(1, 15, 40, 70)),
        _contract("issue", minimum=(1, 15, 40, 70)),
        _contract("security", minimum=(1, 5, 12, 20)),
        _contract("traceability"),
    ],
    "CPM": [
        _contract("architecture", minimum=(1, 2, 4, 6)),
        _contract("design-unit", minimum=(2, 20, 60, 100)),
        _contract("api", minimum=(2, 40, 120, 200)),
        _contract("procedure", minimum=(1, 20, 60, 100)),
        _contract("decision", minimum=(1, 6, 15, 25)),
        _contract("traceability"),
    ],
    "FSM": [
        _contract("firmware-item", minimum=(1, 10, 30, 50)),
        _contract("interface", minimum=(1, 10, 30, 50)),
        _contract("procedure", minimum=(1, 20, 60, 100)),
        _contract("security", minimum=(1, 4, 10, 18)),
        _contract("verification", minimum=(1, 10, 30, 50)),
        _contract("traceability"),
    ],
    "SDSR": [
        _contract("metric", minimum=(2, 15, 35, 60)),
        _contract("issue", minimum=(1, 10, 25, 40)),
        _contract("quality-control", minimum=(1, 10, 25, 40)),
        _contract("assurance", minimum=(1, 6, 15, 25)),
        _contract("deliverable", minimum=(2, 20, 60, 100)),
        _contract("risk", minimum=(1, 8, 20, 35)),
        _contract("traceability"),
    ],
}

# Documents dominated by diagrams/tables are allowed a slightly lower text
# density.  The duplicate and thin-page checks still prevent page-padding.
CHARS_PER_PAGE = {
    "SSS": 260, "IRS": 240, "SSDD": 240, "IDD": 220, "SRS": 260, "SDD": 240,
    "DBDD": 200, "STD": 180, "STR": 160, "SUM": 200, "CPM": 210,
}


def profile_spec(code: str) -> dict[str, Any]:
    code = {"STRP": "STrP"}.get(code.upper(), code.upper())
    pages = PAGE_FLOORS[code]
    page_policy = {
        tier: {
            "minimum_pages": pages[index],
            "minimum_visible_characters": pages[index] * CHARS_PER_PAGE.get(code, 180),
            "maximum_thin_page_ratio": 0.20,
            "maximum_duplicate_page_ratio": 0.08,
        }
        for index, tier in enumerate(TIERS)
    }
    return {
        "schema_version": 1,
        "code": code,
        "purpose": PURPOSES[code],
        "baselines": deepcopy(BASELINES.get(code, {})),
        "source_materials": deepcopy(SOURCE_MATERIALS[code]),
        "artifact_contracts": deepcopy(CONTRACTS[code]),
        "volume_policy": page_policy,
        "release_rules": {
            "allowed_tiers": ["standard", "large", "critical"],
            "tailoring_requires_rationale": True,
            "page_floor_is_repository_policy": True,
        },
    }
