---
name: gjb438c-sdd
description: 按 GJB 438C-2021 编制、修订、审核软件设计说明 SDD 时使用，调用共享核心，固定 document.type=SDD。
---

# SDD · 软件设计说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SDD`，使用其中的章节、字段、数量、来源和基线合同。

目标：描述 CSCI 的设计决策、体系结构、设计单元、接口、数据和执行行为。
来源：已审核 SRS、架构决策记录、代码/模型、接口与数据模型、部署拓扑、异常与并发设计。

```bash
gjb438c init --type SDD --project project.yaml --output docs/SDD.md
gjb438c audit docs/SDD.md --profile review --tier large --baseline-dir working-baselines --json reports/SDD-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SDD.md --profile release --baseline-dir approved-baselines --output dist/SDD.docx
gjb438c audit-docx dist/SDD.docx --profile release
gjb438c audit-volume dist/SDD.docx --source docs/SDD.md --type SDD --tier large
```

必须引用本轮实际审计的 SRS 基线；不能只引用文件名。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
