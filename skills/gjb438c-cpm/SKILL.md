---
name: gjb438c-cpm
description: 按 GJB 438C-2021 编制、修订、审核计算机编程手册 CPM 时使用，调用共享核心，固定 document.type=CPM。
---

# CPM · 计算机编程手册

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type CPM`，使用其中的章节、字段、数量、来源和基线合同。

目标：面向维护开发人员说明代码组织、构建、编码约定、API、并发和测试。
来源：SDD/代码仓库、构建脚本、编码规范、API 文档、数据模型、测试和维护指南。

```bash
gjb438c init --type CPM --project project.yaml --output docs/CPM.md
gjb438c audit docs/CPM.md --profile review --tier large --baseline-dir working-baselines --json reports/CPM-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/CPM.md --profile release --baseline-dir approved-baselines --output dist/CPM.docx
gjb438c audit-docx dist/CPM.docx --profile release
gjb438c audit-volume dist/CPM.docx --source docs/CPM.md --type CPM --tier large
```

代码、命令、API 和模块名须能定位到真实源码；伪代码必须标注，不得宣称未经执行的样例已验证。基线必须本轮实际审计。已有 Markdown 不重新初始化，初始骨架应在 review 失败。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
