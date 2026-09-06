---
name: gjb438c-svd
description: 按 GJB 438C-2021 编制、修订、审核软件版本说明 SVD 时使用，调用共享核心，固定 document.type=SVD。
---

# SVD · 软件版本说明

先读取共享核心 `gjb438c-md-first/SKILL.md`，运行 `gjb438c doctor` 和 `gjb438c profile --type SVD`，使用其中的章节、字段、数量、来源和基线合同。

目标：说明一个发布版本的基线、变更、构建、兼容性、安装和已知问题。
来源：SPS、变更记录、构建流水线、兼容性矩阵、安装升级说明、已知问题与校验值。

```bash
gjb438c init --type SVD --project project.yaml --output docs/SVD.md
gjb438c audit docs/SVD.md --profile review --tier large --baseline-dir working-baselines --json reports/SVD-review.json
# 人工批准及发布条件满足后：
gjb438c render docs/SVD.md --profile release --baseline-dir approved-baselines --output dist/SVD.docx
gjb438c audit-docx dist/SVD.docx --profile release
gjb438c audit-volume dist/SVD.docx --source docs/SVD.md --type SVD --tier large
```

必须引用本轮实际审计的 SPS 基线。已知问题、兼容性和版本校验值依据真实记录，不得自动填写“全部通过”。已有 Markdown 不重新初始化，初始骨架应在 review 失败。机器 PASS 不是人工批准；还需来源语义、字体和逐页视觉验收，不得旁路生成。
