---
name: gjb438c-str
description: 按 GJB 438C-2021 编制、修订、审核软件测试报告 STR 时使用，调用共享核心，固定 document.type=STR。
---

# STR · 软件测试报告

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type STR`，使用其中的章节、字段、数量、来源和基线合同。

目标：记录测试执行事实、结果、偏差、缺陷、覆盖和结论。
来源：STD、执行日志、测试证据、缺陷记录、覆盖率报告、偏差审批与复测记录。

```bash
gjb438c init --type STR --project project.yaml --output docs/STR.md
gjb438c audit docs/STR.md --profile review --tier large --baseline-dir working-baselines --json reports/STR-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/STR.md --profile release --baseline-dir approved-baselines --output dist/STR.docx
gjb438c audit-docx dist/STR.docx --profile release
gjb438c audit-volume dist/STR.docx --source docs/STR.md --type STR --tier large
```

没有真实测试执行证据时只保留 draft，不生成通过结论，不把空执行栏位登记为批准基线。基线必须本轮实际审计。已有 Markdown 不重新初始化，初始骨架应在 review 失败。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
