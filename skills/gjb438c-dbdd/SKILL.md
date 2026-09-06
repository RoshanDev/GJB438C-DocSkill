---
name: gjb438c-dbdd
description: 按 GJB 438C-2021 编制、修订、审核数据库设计说明 DBDD 时使用，调用共享核心，固定 document.type=DBDD。
---

# DBDD · 数据库设计说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type DBDD`，使用其中的章节、字段、数量、来源和基线合同。

目标：描述数据库逻辑/物理模型、表、约束、索引、事务、安全和恢复。
来源：SDD/SSDD、数据字典、ER 模型、DDL、容量与性能预算、备份恢复与迁移方案。

```bash
gjb438c init --type DBDD --project project.yaml --output docs/DBDD.md
gjb438c audit docs/DBDD.md --profile review --tier large --baseline-dir working-baselines --json reports/DBDD-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/DBDD.md --profile release --baseline-dir approved-baselines --output dist/DBDD.docx
gjb438c audit-docx dist/DBDD.docx --profile release
gjb438c audit-volume dist/DBDD.docx --source docs/DBDD.md --type DBDD --tier large
```

基线必须本轮实际审计。真实表数量不足时提出适用性剪裁，由项目所有者批准，不能虚构表凑数。已有 Markdown 不重新初始化，初始骨架应在 review 失败。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
