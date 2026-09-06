---
name: gjb438c-ssdd
description: 按 GJB 438C-2021 编制、修订、审核系统/子系统设计说明 SSDD 时使用，调用共享核心，固定 document.type=SSDD。
---

# SSDD · 系统/子系统设计说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SSDD`，使用其中的章节、字段、数量、来源和基线合同。

目标：描述系统/子系统级设计决策、体系结构、执行方案和分配关系。
来源：SSS 基线、架构决策记录、系统分解、硬软件分配、接口与数据设计、部署与执行模型。

```bash
gjb438c init --type SSDD --project project.yaml --output docs/SSDD.md
gjb438c audit docs/SSDD.md --profile review --tier large --baseline-dir working-baselines --json reports/SSDD-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SSDD.md --profile release --baseline-dir approved-baselines --output dist/SSDD.docx
gjb438c audit-docx dist/SSDD.docx --profile release
gjb438c audit-volume dist/SSDD.docx --source docs/SSDD.md --type SSDD --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
