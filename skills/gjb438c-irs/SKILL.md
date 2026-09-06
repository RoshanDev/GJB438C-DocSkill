---
name: gjb438c-irs
description: 按 GJB 438C-2021 编制、修订、审核接口需求规格说明 IRS 时使用，调用共享核心，固定 document.type=IRS。
---

# IRS · 接口需求规格说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type IRS`，使用其中的章节、字段、数量、来源和基线合同。

目标：定义实体之间一个或多个接口的可验证需求。
来源：接口控制资料、上下游实体规格、协议标准、数据字典、时序与错误场景、安全约束。

```bash
gjb438c init --type IRS --project project.yaml --output docs/IRS.md
gjb438c audit docs/IRS.md --profile review --tier large --baseline-dir working-baselines --json reports/IRS-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/IRS.md --profile release --baseline-dir approved-baselines --output dist/IRS.docx
gjb438c audit-docx dist/IRS.docx --profile release
gjb438c audit-volume dist/IRS.docx --source docs/IRS.md --type IRS --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
