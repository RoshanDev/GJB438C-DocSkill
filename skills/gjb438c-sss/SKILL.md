---
name: gjb438c-sss
description: 按 GJB 438C-2021 编制、修订、审核系统/子系统规格说明 SSS 时使用，调用共享核心，固定 document.type=SSS。
---

# SSS · 系统/子系统规格说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SSS`，使用其中的章节、字段、数量、来源和基线合同。

目标：定义系统/子系统需求、外部接口、质量特性和鉴定检验方法。
来源：任务需求、总体技术要求、OCD、系统边界与外部接口、质量特性指标、鉴定检验方法。

```bash
gjb438c init --type SSS --project project.yaml --output docs/SSS.md
gjb438c audit docs/SSS.md --profile review --tier large --baseline-dir working-baselines --json reports/SSS-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SSS.md --profile release --baseline-dir approved-baselines --output dist/SSS.docx
gjb438c audit-docx dist/SSS.docx --profile release
gjb438c audit-volume dist/SSS.docx --source docs/SSS.md --type SSS --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
