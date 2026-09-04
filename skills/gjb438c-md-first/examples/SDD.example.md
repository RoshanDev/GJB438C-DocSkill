---
document:
  type: SDD
  title: 软件设计说明
  id: DEMO-SDD-001
  version: V1.0
  status: release
  standard_clause: '5.11'
  appendix: K
software:
  name: 示例任务管理软件
  version: V1.0
  identifier: DEMO-CSCI
organization: 示例研制单位
classification: 公开
date: '2026-09-04'
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
    description: 建立软件设计说明示例
    author: 示例项目组
sources:
  - id: SRC-SRS
    path: examples/SRS.example.md
    version: V1.0
  - id: SRC-DESIGN-BASELINE
    path: examples/design-baseline.md
    version: V1.0
---

# 软件设计说明

# 1 范围

## 1.1 标识

本文档描述示例任务管理软件配置项的设计，软件标识为 DEMO-CSCI，软件版本和文档版本均为 V1.0。

## 1.2 系统概述

系统由接入服务、任务服务、任务执行器、状态服务、关系数据库和审计服务组成。本文档仅演示设计证据与需求追踪方法，不代表任何真实项目实现。

# 2 引用文档

表 2-1 引用文档

| 标识 | 名称 | 版本 |
|---|---|---|
| SRC-SRS | 软件需求规格说明示例 | V1.0 |
| SRC-DESIGN-BASELINE | 示例设计基线 | V1.0 |

# 3 CSCI 级设计决策

系统将任务执行与任务状态提交分离，并由状态服务统一校验任务状态转换。访问控制在接入边界执行，审计服务记录关键结果。

# 4 CSCI 体系结构设计

## 4.1 体系结构组成

接入服务负责协议处理；任务服务负责受理和查询；任务执行器执行具体任务；状态服务校验并提交状态；关系数据库保存任务和审计索引。

## 4.2 执行概念

任务服务在事务中创建任务；执行器领取任务并产生状态事件；状态服务校验前态、事件序号和终态约束后提交结果。

## 4.3 接口设计

外部接口使用 HTTPS/JSON；内部任务事件采用持久消息通道。所有受保护操作携带身份和关联标识。

# 5 CSCI 详细设计

## 5.1 任务管理单元

任务管理单元负责受理、领取、执行状态接收、查询、取消和超时处理，并保证终态稳定。

## 5.2 访问控制单元

访问控制单元负责认证、角色授权、拒绝处理和审计上下文传递。

# 6 需求可追踪性

表 6-1 需求—设计映射

| SRS 需求 | 设计单元 | 验证 |
|---|---|---|
| REQ-TASK-001 | DU-TASK | VT-TASK-001 |
| REQ-ACCESS-001 | DU-ACCESS | VT-ACCESS-001 |

# 7 注释

“统一提交”表示所有任务状态变化使用同一套状态转换校验规则，不限定具体部署进程数量。

# 附录A 质量门禁数据块

```gjb-decision
id: ADR-TASK-001
context: 多个任务执行器可能产生重复、乱序或迟到事件，若直接覆盖状态会导致终态回退。
options: [执行器直接更新任务记录, 状态服务统一校验并提交, 使用全局互斥锁串行执行]
decision: 采用状态服务统一校验并提交任务状态。
rationale: 该方案集中状态机、幂等和终态保护规则，同时允许任务执行器独立扩展。
consequences: 状态服务需要高可用和积压监控；事件记录需要保留恢复所需序号。
status: accepted
source_refs: [SRC-SRS#REQ-TASK-001, SRC-DESIGN-BASELINE#state-model]
```

```gjb-architecture
id: ARCH-DEMO-001
components: [接入服务, 任务服务, 任务执行器, 状态服务, 关系数据库, 审计服务]
connectors: [HTTPS/JSON, 内部服务调用, 持久消息通道, 数据库事务]
deployment: 无状态服务可多副本部署；状态服务采用活动实例协调；数据库使用受保护持久存储。
failure_domains: 接入服务和执行器故障不影响已提交状态；状态服务或数据库故障触发暂停领取和告警。
source_refs: [SRC-DESIGN-BASELINE#architecture]
```

```gjb-design-unit
id: DU-TASK
requirements: [REQ-TASK-001]
responsibility: 管理任务受理后的领取、执行事件、状态提交、取消、超时和结果查询。
behavior: 执行器领取任务并产生带序号事件；状态服务校验前态、事件序号和终态约束后提交状态。
interfaces: [IF-TASK-API, IF-TASK-EVENT]
data: [DM-TASK]
states: [Pending, Running, Succeeded, Failed, Cancelled, TimedOut]
errors: 领取超时允许重新领取；重复事件幂等忽略；非法转换进入隔离记录并告警。
concurrency: 任务版本号采用乐观并发控制，同一任务只允许按事件序号单调推进。
security: 查询和取消按角色授权；所有状态变化生成审计记录。
deployment: 任务执行器多副本；状态服务两个候选实例中仅一个活动实例提交状态。
verification: [VT-TASK-001]
source_refs: [SRC-SRS#REQ-TASK-001, ADR-TASK-001]
```

```gjb-design-unit
id: DU-ACCESS
requirements: [REQ-ACCESS-001]
responsibility: 对受保护接口执行身份认证、角色授权、拒绝处理和审计上下文传递。
behavior: 请求通过认证和角色检查后进入任务服务；拒绝请求不产生业务任务，但生成审计记录。
interfaces: [IF-ACCESS-API]
data: [DM-TASK]
states: [Allowed, Rejected]
errors: 未认证返回 401，无权限返回 403，参数非法返回 400，服务不可用返回 503。
concurrency: 同一关联标识的重复请求使用幂等键避免重复创建任务。
security: 强制加密传输、令牌校验、最小权限和审计字段脱敏。
deployment: 多副本无状态部署，经受控入口提供服务。
verification: [VT-ACCESS-001]
source_refs: [SRC-SRS#REQ-ACCESS-001, SRC-DESIGN-BASELINE#access-control]
```

```gjb-interface
id: IF-TASK-API
provider: DU-TASK
consumer: DU-ACCESS
protocol: 受控内部服务接口
input: 任务类型、规范化参数、主体标识、角色集合和幂等键
output: 任务标识、受理状态或稳定错误对象
timing: 数据库可用时 2 秒内返回受理结果；执行结果通过查询接口获得。
errors: 参数非法、幂等冲突、存储不可用和身份上下文缺失返回稳定错误码。
security: 仅接受完成认证授权的调用，主体和角色上下文不可由下游覆盖。
compatibility: 接口采用语义版本；新增可选字段不得破坏上一稳定版本调用方。
source_refs: [SRC-SRS#REQ-TASK-001, SRC-DESIGN-BASELINE#task-boundary]
```

```gjb-interface
id: IF-TASK-EVENT
provider: DU-TASK
consumer: 状态服务
protocol: 持久消息通道
input: task_id、event_id、sequence、previous_state、target_state、payload、occurred_at
output: 提交确认、幂等忽略、隔离或拒绝结果
timing: 同一 task_id 的事件按 sequence 单调处理；积压时不得跳过一致性校验。
errors: 重复事件幂等忽略，序号缺口暂停推进，非法转换进入隔离记录并告警。
security: 生产者使用服务身份认证，消息通道实施最小权限和完整性校验。
compatibility: 事件模式携带 schema_version，消费者兼容当前和上一稳定版本。
source_refs: [SRC-SRS#REQ-TASK-001, ADR-TASK-001]
```

```gjb-interface
id: IF-ACCESS-API
provider: DU-ACCESS
consumer: 示例客户端
protocol: HTTPS/JSON
input: 操作请求、身份令牌、关联标识和幂等键
output: HTTP 状态、任务标识或错误对象
timing: 认证授权判定在 1 秒内完成，长时任务结果通过任务查询获得。
errors: 400/401/403/409/429/500，错误对象包含稳定错误码和关联标识。
security: TLS 1.2 及以上、令牌认证、角色授权、请求限流和审计脱敏。
compatibility: 外部接口采用版本前缀，兼容期内保留上一稳定版本。
source_refs: [SRC-SRS#REQ-ACCESS-001, SRC-DESIGN-BASELINE#external-api]
```

```gjb-data
id: DM-TASK
owner: 状态服务
schema: Task(id, type, state, version, progress, result, error, created_at, updated_at)
constraints: id 全局唯一；version 单调递增；终态不可回退；id 和 state 建索引。
transaction: 状态、版本和审计索引在同一数据库事务中提交。
retention: 在线保留 90 天，归档期限由项目数据策略配置。
security: 最小权限数据库账号、字段脱敏和备份加密。
recovery: 通过数据库备份和事件记录恢复，恢复后校验状态和版本单调性。
source_refs: [SRC-SRS#REQ-TASK-001, ADR-TASK-001]
```

```gjb-scenario
id: SCN-TASK-COMPLETE
requirements: [REQ-TASK-001, REQ-ACCESS-001]
trigger: 已认证且具备相应角色的用户提交一个有效任务。
preconditions: 认证服务、数据库和消息通道可用。
steps: [接入服务完成认证授权, 任务服务创建 Pending 任务, 执行器领取并置为 Running, 状态服务提交 Succeeded, 用户查询结果]
failures: [执行器故障后重新领取, 重复完成事件被幂等忽略, 非法状态转换进入隔离记录]
postconditions: 任务处于稳定终态，结果和审计记录可查询。
observability: 记录受理时延、执行时延、重试次数、事件积压、拒绝请求和非法转换数量。
source_refs: [SRC-SRS#REQ-TASK-001, SRC-SRS#REQ-ACCESS-001]
```

```gjb-deployment
id: DEPLOY-DEMO-001
nodes: 应用节点和数据库节点。
placement: 接入服务、任务服务和执行器分散部署；状态服务活动实例由租约协调。
resources: 各组件配置处理器和内存上下限，生产值由容量测试证据确定。
network: 对外仅开放受控 HTTPS 入口，内部服务和消息通道使用受限网络区域。
storage: 关系数据库使用持久存储和独立备份介质。
upgrade: 先执行兼容性检查和数据迁移，再滚动升级无状态服务，最后升级状态服务。
rollback: 保留上一版本制品和可逆数据迁移；回滚前检查状态模式兼容性。
source_refs: [SRC-DESIGN-BASELINE#deployment]
```

```gjb-security
id: SEC-DEMO-001
assets: [身份令牌, 任务参数, 任务结果, 审计记录, 数据库备份]
threats: [越权访问, 重放请求, 敏感信息泄露, 审计篡改, 制品替换]
controls: [加密传输, 角色授权, 幂等键, 日志脱敏, 审计归档, 制品摘要校验]
audit: 记录主体、角色、动作、资源、结果、错误码、关联标识和时间。
residual_risk: 高权限凭据泄露仍可能扩大影响，需要由凭据轮换和异常检测降低风险。
source_refs: [SRC-SRS#REQ-ACCESS-001, SRC-DESIGN-BASELINE#security]
```

```gjb-verification
id: VT-TASK-001
target: REQ-TASK-001 与 DU-TASK
method: 故障注入测试、并发测试和状态机检查
criteria: 任务在规定时间内可查询；重复、乱序和迟到事件不导致终态回退；故障恢复后状态与审计一致。
evidence: 测试记录、数据库快照、事件序列和监控截图
source_refs: [SRC-SRS#REQ-TASK-001]
```

```gjb-verification
id: VT-ACCESS-001
target: REQ-ACCESS-001 与 DU-ACCESS
method: 接口测试、权限测试和审计检查
criteria: 受保护接口强制认证和角色授权；拒绝响应与审计字段符合接口约定；拒绝请求不创建业务任务。
evidence: 接口测试报告、权限测试记录和审计日志
source_refs: [SRC-SRS#REQ-ACCESS-001]
```

```gjb-traceability
id: TRACE-SDD-001
source_refs: [SRC-SRS]
requirements: [REQ-TASK-001, REQ-ACCESS-001]
forward_targets: [DU-TASK, DU-ACCESS, VT-TASK-001, VT-ACCESS-001]
```
