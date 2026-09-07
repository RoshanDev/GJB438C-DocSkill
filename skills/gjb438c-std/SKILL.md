---
name: gjb438c-std
description: 按 GJB 438C-2021 编制、修订、审核软件测试说明 STD 时使用，调用共享核心，固定 document.type=STD。
---

# STD · 软件测试说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type STD`，使用其中的章节、字段、数量、来源和基线合同。

目标：规定每个测试用例的设置、数据、步骤、检查点、判据和追踪。
来源：STP、需求基线、接口需求、环境配置、测试数据、自动化脚本与判据。

```bash
gjb438c init --type STD --project project.yaml --output docs/STD.md
gjb438c audit docs/STD.md --profile review --tier large --baseline-dir working-baselines --json reports/STD-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/STD.md --profile release --baseline-dir approved-baselines --output dist/STD.docx
gjb438c audit-docx dist/STD.docx --profile release
gjb438c audit-volume dist/STD.docx --source docs/STD.md --type STD --tier large
```

必须引用本轮实际审计的基线。每条用例独立可执行，不能用编号范围或用例组冒充多条用例。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier 或虚构批准。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
