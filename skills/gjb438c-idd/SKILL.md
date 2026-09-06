---
name: gjb438c-idd
description: 按 GJB 438C-2021 编制、修订、审核接口设计说明 IDD 时使用，调用共享核心，固定 document.type=IDD。
---

# IDD · 接口设计说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type IDD`，使用其中的章节、字段、数量、来源和基线合同。

目标：描述接口设计、消息、协议、状态、时序、错误和兼容性。
来源：IRS 基线、协议/消息定义、API/总线规范、状态机与时序、错误码、兼容性策略。

```bash
gjb438c init --type IDD --project project.yaml --output docs/IDD.md
gjb438c audit docs/IDD.md --profile review --tier large --baseline-dir working-baselines --json reports/IDD-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/IDD.md --profile release --baseline-dir approved-baselines --output dist/IDD.docx
gjb438c audit-docx dist/IDD.docx --profile release
gjb438c audit-volume dist/IDD.docx --source docs/IDD.md --type IDD --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
