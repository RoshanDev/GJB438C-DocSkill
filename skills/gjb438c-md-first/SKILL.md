---
name: gjb438c-md-first
description: 当用户要求生成、修订、审核或转换 GJB 438C-2021 文档，提到 SDP、SIP、STrP、STP、OCD、SSS、IRS、SSDD、IDD、SRS、SDD、DBDD、STD、STR、SPS、SVD、SUM、CPM、FSM、SDSR，或要求统一首页、Markdown 转 Word、Word 回流 Markdown、需求追踪、设计覆盖率时使用。
---

# GJB 438C Markdown-first 文档工程

## 不可违反的规则

1. 先确定文档类型，再从该类型的真实 DOCX 模板抽取章节结构；不得把所有文档强套同一目录。
2. 评审期间 Markdown 是内容基线；除非用户明确要求只改 Word 格式，不直接在生成后的 DOCX 中批量重写业务语义。
3. 不编造项目事实、标准条文、测试结论、版本兼容性、接口、性能或来源证据。缺失信息在 draft 阶段显式标记，release 阶段必须消除。
4. 首页、签字页、变更履历使用 `templates/front-matter/standard-front-matter.docx`，不得以通用封面替代。
5. SDD/SSDD 必须绑定已审核需求基线，建立需求到设计单元/场景/验证的双向映射。
6. 发布 Word 必须经过内容审计、DOCX 审计、目录刷新和逐页视觉检查。

## 标准工作流

1. 收集合同、需求、既有文档、代码、接口、数据库、部署、测试和决策记录，建立来源清单。
2. 运行 `gjb438c init --type <TYPE>`，从真实模板生成 Markdown 骨架。
3. 按章节编写业务正文，并用 `gjb-*` YAML 数据块记录稳定需求、设计、接口、数据、场景、验证和追踪证据。
4. 运行 `gjb438c audit`。SRS 使用 release 门禁后，SDD 再通过 `--baseline-srs` 引用该基线。
5. 运行 `gjb438c render ... --refresh-toc` 生成 Word。
6. 运行 `gjb438c audit-docx --profile release`，随后将 DOCX 渲染为逐页图片进行视觉验收。
7. Word 中发生实质正文修改后，运行 `gjb438c import-word` 回流候选 Markdown，并重新执行第 4～6 步。

## 格式锁

- 目录标题：三号宋体、1.5 倍行距、居中。
- 目录文字：小四宋体、1.5 倍行距、两端对齐。
- 各级标题：小四黑体、1.5 倍行距。
- 正文：小四宋体、1.5 倍行距、两端对齐。
- 图名/表名：五号黑体、单倍行距、居中。
- 表内文字：五号宋体、单倍行距。
- 西文：Times New Roman。
- 目录和页码必须是 Word 原生域，不得用手写页码冒充。
