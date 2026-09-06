---
name: gjb438c-sum
description: 按 GJB 438C-2021 编制、修订、审核软件用户手册 SUM 时使用，调用共享核心，固定 document.type=SUM。
---

# SUM · 软件用户手册

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SUM`，使用其中的章节、字段、数量、来源和基线合同。

目标：面向用户说明任务、操作、界面、错误处理、故障排查和安全注意事项。
来源：需求和版本说明、交互原型/截图、用户任务、错误与告警、故障排查、安全使用要求。

```bash
gjb438c init --type SUM --project project.yaml --output docs/SUM.md
gjb438c audit docs/SUM.md --profile review --tier large --baseline-dir working-baselines --json reports/SUM-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SUM.md --profile release --baseline-dir approved-baselines --output dist/SUM.docx
gjb438c audit-docx dist/SUM.docx --profile release
gjb438c audit-volume dist/SUM.docx --source docs/SUM.md --type SUM --tier large
```

操作步骤和截图必须与真实版本一致，不得创造不存在的界面或功能。基线必须本轮实际审计。已有 Markdown 不重新初始化，初始骨架应在 review 失败。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
