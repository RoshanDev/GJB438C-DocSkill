# Markdown 内容契约与质量门禁

## YAML front matter

每份文档必须声明文档类型、标题、标识号、版本、状态，软件名称/版本/标识，编制单位、密级、日期，前三页字段、签字角色、修订记录和来源清单。

```yaml
---
document:
  type: SDD
  title: 示例任务管理软件软件设计说明
  id: DEMO-SDD-001
  version: V1.0
  status: release
software:
  name: 示例任务管理软件
  version: V1.3
  identifier: DEMO-CSCI
organization: 示例研制单位
classification: 公开
date: 2026-09-04
front_matter:
  template: templates/front-matter/standard-front-matter.docx
  archive_id: DEMO-2026-002
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
    description: 建立文档初稿
    author: 项目组
sources:
  - id: SRC-SRS
    path: docs/SRS.md
    version: V1.0
---
```

## 结构化证据块

正文照常使用 Markdown。需要自动审计的事实以 `gjb-*` fenced block 表达，数据内容为 YAML。这些块默认不会直接显示在 Word 正文中，而是作为质量门禁和追踪数据。

### SRS 需求

````markdown
```gjb-requirement
id: REQ-OPS-001
statement: 系统应把长时操作表示为可查询、可审计的统一任务。
rationale: 避免控制器重启或事件乱序时任务终态回退。
source: SRC-PRODUCT-BASELINE#5.3
priority: P0
verification: [test, analysis]
acceptance:
  - 在任务进入成功终态后注入重复或迟到事件，状态仍保持成功且审计记录可查询。
```
````

release 门禁会检查稳定标识、`应`式义务、理由、来源、优先级、验证方法和可判定验收准则。

### SDD 设计单元

````markdown
```gjb-design-unit
id: DU-OPERATION-PROJECTOR
requirements: [REQ-OPS-001]
responsibility: 将事件按单一状态转换规则投影为任务状态。
behavior: 读取事件并在数据库事务中校验前态、事件序号和终态规则。
interfaces: [IF-OPERATION-EVENT]
data: [DM-OPERATION]
states: [Pending, Running, Succeeded, Failed, Cancelled, TimedOut]
errors: 重复、乱序和迟到事件不改变已确认终态，并写入审计记录。
concurrency: 通过行级事务与事件序号实现每个任务的串行状态转换。
security: 只接受携带内部服务身份且通过授权检查的事件。
deployment: 多副本部署；数据库事务是状态一致性边界。
verification: [VT-OPS-001]
source_refs: [SRC-SRS#REQ-OPS-001, SRC-ARCH#ADR-001]
```
````

SDD/SSDD 发布门禁还会检查：

- 设计决策是否记录背景、候选方案、选择理由、后果和状态；
- 总体架构是否描述组件、连接、部署与故障域；
- 接口是否覆盖提供者、消费者、协议、输入输出、时序、错误、安全和兼容性；
- 数据是否覆盖所有者、模式、约束、事务、保留、安全和恢复；
- 关键场景是否覆盖触发、前置条件、步骤、失败分支、后置条件与可观测性；
- SRS 需求是否全部映射到设计单元或关键场景；
- SDD 是否引用了需求基线中不存在的标识。

## draft / review / release

- `draft`：允许占位信息，以警告为主，适合搭骨架。
- `review`：核心需求/设计字段和追踪缺失会阻断，允许前三页签字为空。
- `release`：占位内容、无来源结论、未刷新的目录、需求覆盖缺失和前三页关键字段均阻断。
