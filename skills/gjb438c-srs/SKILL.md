---
name: gjb438c-srs
description: 按 GJB 438C-2021 编制、修订、审核软件需求规格说明 SRS 时使用，调用共享核心，固定 document.type=SRS。
---

# SRS · 软件需求规格说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SRS`，使用其中的章节、字段、数量、来源和基线合同。

目标：定义 CSCI 的完整、无歧义、可验证和可追踪需求。
来源：SSS/OCD/合同需求、用户场景、接口需求、性能与资源预算、质量特性、验收与验证依据。

```bash
gjb438c init --type SRS --project project.yaml --output docs/SRS.md
gjb438c audit docs/SRS.md --profile review --tier large --baseline-dir working-baselines --json reports/SRS-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SRS.md --profile release --baseline-dir approved-baselines --output dist/SRS.docx
gjb438c audit-docx dist/SRS.docx --profile release
gjb438c audit-volume dist/SRS.docx --source docs/SRS.md --type SRS --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
