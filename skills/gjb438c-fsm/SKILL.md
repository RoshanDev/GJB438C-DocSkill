---
name: gjb438c-fsm
description: 按 GJB 438C-2021 编制、修订、审核固件保障手册 FSM 时使用，调用共享核心，固定 document.type=FSM。
---

# FSM · 固件保障手册

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type FSM`，使用其中的章节、字段、数量、来源和基线合同。

目标：说明固件目标、硬件接口、烧写、升级、回退、诊断和恢复。
来源：固件映像、硬件规格、存储布局、烧写/升级工具、诊断记录、恢复与完整性方案。

```bash
gjb438c init --type FSM --project project.yaml --output docs/FSM.md
gjb438c audit docs/FSM.md --profile review --tier large --baseline-dir working-baselines --json reports/FSM-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/FSM.md --profile release --baseline-dir approved-baselines --output dist/FSM.docx
gjb438c audit-docx dist/FSM.docx --profile release
gjb438c audit-volume dist/FSM.docx --source docs/FSM.md --type FSM --tier large
```

没有自研固件时先提出适用性及剪裁决定，供项目所有者批准；不要把普通软件组件改名为固件凑数。基线必须本轮实际审计。已有 Markdown 不重新初始化，初始骨架应在 review 失败。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
