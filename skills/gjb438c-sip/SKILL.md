---
name: gjb438c-sip
description: 按 GJB 438C-2021 编制、修订、审核软件安装计划 SIP 时使用，调用共享核心，固定 document.type=SIP。
---

# SIP · 软件安装计划

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SIP`，使用其中的章节、字段、数量、来源和基线合同。

目标：策划用户现场的软件安装、转换、培训、验证和回退。
来源：产品规格与版本说明、现场调查记录、部署拓扑、安装脚本与配置、培训计划、回退方案。

```bash
gjb438c init --type SIP --project project.yaml --output docs/SIP.md
gjb438c audit docs/SIP.md --profile review --tier large --baseline-dir working-baselines --json reports/SIP-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SIP.md --profile release --baseline-dir approved-baselines --output dist/SIP.docx
gjb438c audit-docx dist/SIP.docx --profile release
gjb438c audit-volume dist/SIP.docx --source docs/SIP.md --type SIP --tier large
```

没有上游依赖时可省略 baseline-dir；存在依赖时必须引用本轮实际审计的基线。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier、虚构条目或批准、将未执行测试宣称通过。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
