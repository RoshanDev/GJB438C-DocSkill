---
name: gjb438c-ocd
description: 按 GJB 438C-2021 编制、修订、审核运行方案说明 OCD 时使用，调用共享核心，固定 document.type=OCD。
---

# OCD · 运行方案说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type OCD`，使用其中的章节、字段、数量、来源和基线合同。

目标：描述用户需要、运行环境、使用方式、任务场景和与现有系统的关系。
来源：用户访谈、任务流程、运行规程、现有系统资料、典型/异常/降级场景、环境约束。

```bash
gjb438c init --type OCD --project project.yaml --output docs/OCD.md
gjb438c audit docs/OCD.md --profile review --tier large --baseline-dir working-baselines --json reports/OCD-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/OCD.md --profile release --baseline-dir approved-baselines --output dist/OCD.docx
gjb438c audit-docx dist/OCD.docx --profile release
gjb438c audit-volume dist/OCD.docx --source docs/OCD.md --type OCD --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
