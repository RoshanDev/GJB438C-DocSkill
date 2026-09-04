---
document:
  type: SRS
  title: 软件需求规格说明
  id: DEMO-SRS-001
  version: V1.0
  status: release
  standard_clause: '5.10'
  appendix: J
software:
  name: 示例任务管理软件
  version: V1.0
  identifier: DEMO-CSCI
organization: 示例研制单位
classification: 公开
date: '2026-09-04'
front_matter:
  template: templates/front-matter/standard-front-matter.docx
  archive_id: DEMO-2026-001
  project_code: DEMO
  phase: 研制
  date_cn: 二〇二六年九月
signatures:
  prepared: {name: '', date: ''}
  reviewed: {name: '', date: ''}
  standard_reviewed: {name: '', date: ''}
  countersigned: {name: '', date: ''}
  approved: {name: '', date: ''}
revisions:
  - date: '2026.09.04'
    version: V1.0
    description: 建立软件需求规格说明示例
    author: 示例项目组
sources:
  - id: SRC-DEMO-BASELINE
    path: examples/source-baseline.md
    version: V1.0
---

# 软件需求规格说明

# 1 范围

## 1.1 标识

本文档适用于示例任务管理软件配置项，软件标识为 DEMO-CSCI，软件版本和文档版本均为 V1.0。

## 1.2 系统概述

系统用于接收、执行和查询长时任务，并为不同角色提供受控访问、状态跟踪和审计记录。本文档仅作为公开示例，不包含真实项目、单位、人员、地址或运行环境信息。

# 2 引用文档

表 2-1 引用文档

| 标识 | 名称 | 版本 |
|---|---|---|
| SRC-DEMO-BASELINE | 示例产品基线 | V1.0 |

# 3 需求

## 3.1 任务管理需求

系统应为每个有效任务建立稳定标识，并允许授权用户查询任务状态和结果。

## 3.2 访问控制需求

系统应对受保护操作实施身份认证、角色授权和审计记录。

# 4 合格性规定

每项需求通过测试、分析、检查或演示验证，并保存输入条件、步骤、预期结果、实际结果和证据编号。

# 5 需求可追踪性

本节的正向和逆向关系由附录中的结构化质量数据块生成和审核。

# 6 注释

“任务终态”包括成功、失败、取消和超时；终态一经确认，不得因重复或迟到事件回退。

# 附录A 质量门禁数据块

```gjb-requirement
id: REQ-TASK-001
statement: 系统应为每个有效长时任务创建全局唯一标识，并允许授权用户查询任务状态、进度、结果和错误信息。
rationale: 稳定任务标识和可查询状态用于支持异步执行、故障恢复和审计追踪。
source: SRC-DEMO-BASELINE#REQ-TASK
priority: P0
verification: [测试, 检查]
acceptance:
  - 提交一个有效任务后 2 秒内，查询接口返回同一任务标识和非空状态。
  - 任务进入终态后重复提交相同完成事件，任务状态和结果保持不变。
```

```gjb-requirement
id: REQ-ACCESS-001
statement: 系统应对受保护操作实施身份认证和角色授权，并记录允许或拒绝结果及关联标识。
rationale: 访问控制和审计用于限制未授权操作并支持事后追溯。
source: SRC-DEMO-BASELINE#REQ-ACCESS
priority: P0
verification: [测试, 分析]
acceptance:
  - 未认证用户访问受保护接口时，系统返回 401 且不创建任务。
  - 已认证但无相应角色的用户执行受限操作时，系统返回 403，并生成包含主体、动作、结果和关联标识的审计记录。
```

```gjb-traceability
id: TRACE-SRS-001
source_refs: [SRC-DEMO-BASELINE]
requirements: [REQ-TASK-001, REQ-ACCESS-001]
forward_targets: [SDD:DU-TASK, SDD:DU-ACCESS]
```
