---
name: gjb438c-sps
description: 按 GJB 438C-2021 编制、修订、审核软件产品规格说明 SPS 时使用，调用共享核心，固定 document.type=SPS。
---

# SPS · 软件产品规格说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SPS`，使用其中的章节、字段、数量、来源和基线合同。

目标：精确定义可交付软件产品、组成、构建、配置、安装、运行和完整性。
来源：构建产物、SBOM/依赖、配置基线、安装与运行信息、完整性校验、限制条件。

```bash
gjb438c init --type SPS --project project.yaml --output docs/SPS.md
gjb438c audit docs/SPS.md --profile review --tier large --baseline-dir working-baselines --json reports/SPS-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SPS.md --profile release --baseline-dir approved-baselines --output dist/SPS.docx
gjb438c audit-docx dist/SPS.docx --profile release
gjb438c audit-volume dist/SPS.docx --source docs/SPS.md --type SPS --tier large
```

必须引用本轮实际审计的基线。制品版本与校验和须来自真实构建，不得虚构。已有 Markdown 不重新初始化，初始骨架应在 review 失败。禁止降低 tier 或伪造批准。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
