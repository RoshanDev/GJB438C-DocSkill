---
name: gjb438c-sdsr
description: 按 GJB 438C-2021 编制、修订、审核软件研制总结报告 SDSR 时使用，调用共享核心，固定 document.type=SDSR。
---

# SDSR · 软件研制总结报告

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SDSR`，使用其中的章节、字段、数量、来源和基线合同。

目标：总结研制结果、度量、重大问题、质量控制、保证活动和经验教训。
来源：SDP 与历次修订、需求/设计/测试基线、度量数据、重大问题闭环、质量保证记录、交付与版本清单。

```bash
gjb438c init --type SDSR --project project.yaml --output docs/SDSR.md
gjb438c audit docs/SDSR.md --profile review --tier large --baseline-dir working-baselines --json reports/SDSR-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SDSR.md --profile release --baseline-dir approved-baselines --output dist/SDSR.docx
gjb438c audit-docx dist/SDSR.docx --profile release
gjb438c audit-volume dist/SDSR.docx --source docs/SDSR.md --type SDSR --tier large
```

总结中的完成与通过结论必须来自真实记录，未执行 STR 不能作为批准基线。必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
