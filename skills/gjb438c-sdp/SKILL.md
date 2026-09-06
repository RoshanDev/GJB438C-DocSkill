---
name: gjb438c-sdp
description: 按 GJB 438C-2021 编制、修订、审核软件开发计划 SDP 时使用，调用共享核心，固定 document.type=SDP。
---

# SDP · 软件开发计划

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SDP`，使用其中的章节、字段、数量、来源和基线合同。

目标：策划并控制软件开发全过程、方法、资源、进度、风险和保证活动。
来源：合同/技术协议、生存周期模型、WBS 与里程碑、组织和资源计划、风险清单、保证与配置管理制度。

```bash
gjb438c init --type SDP --project project.yaml --output docs/SDP.md
gjb438c audit docs/SDP.md --profile review --tier large --baseline-dir working-baselines --json reports/SDP-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SDP.md --profile release --baseline-dir approved-baselines --output dist/SDP.docx
gjb438c audit-docx dist/SDP.docx --profile release
gjb438c audit-volume dist/SDP.docx --source docs/SDP.md --type SDP --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
