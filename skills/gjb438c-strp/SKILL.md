---
name: gjb438c-strp
description: 按 GJB 438C-2021 编制、修订、审核软件移交计划 STrP 时使用，调用共享核心，固定 document.type=STrP。
---

# STrP · 软件移交计划

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type STrP`，使用其中的章节、字段、数量、来源和基线合同。

目标：策划向保障机构移交软件产品、资源、知识和责任。
来源：交付清单、配置基线、保障资源清单、培训资料、知识转移计划、验收准则。

```bash
gjb438c init --type STrP --project project.yaml --output docs/STrP.md
gjb438c audit docs/STrP.md --profile review --tier large --baseline-dir working-baselines --json reports/STrP-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/STrP.md --profile release --baseline-dir approved-baselines --output dist/STrP.docx
gjb438c audit-docx dist/STrP.docx --profile release
gjb438c audit-volume dist/STrP.docx --source docs/STrP.md --type STrP --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
