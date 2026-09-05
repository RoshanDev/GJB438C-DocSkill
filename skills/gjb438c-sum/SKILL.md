---
name: gjb438c-sum
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件用户手册（SUM、5.17、附录Q）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SUM；Markdown 是评审基线，DOCX 是发布物。
---

# SUM · 软件用户手册

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SUM --project <project.yaml> --output docs/SUM.md
gjb438c audit docs/SUM.md --profile review
gjb438c render docs/SUM.md --output dist/SUM.docx --profile release --refresh-toc
gjb438c audit-docx dist/SUM.docx --profile release
gjb438c audit-volume dist/SUM.docx --type SUM --tier large
```

## 编写目标

面向用户说明任务、操作、界面、错误处理、故障排查和安全注意事项。

## 首要来源材料

需求和版本说明、交互原型/截图、用户任务、错误与告警、故障排查、安全使用要求。

## 基线关系

固定必选：无固定必选基线；至少提供其一：SRS, SVD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/sum.yaml`。
