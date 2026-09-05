---
name: gjb438c-sss
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 系统/子系统规格说明（SSS、5.6、附录F）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SSS；Markdown 是评审基线，DOCX 是发布物。
---

# SSS · 系统/子系统规格说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SSS --project <project.yaml> --output docs/SSS.md
gjb438c audit docs/SSS.md --profile review
gjb438c render docs/SSS.md --output dist/SSS.docx --profile release --refresh-toc
gjb438c audit-docx dist/SSS.docx --profile release
gjb438c audit-volume dist/SSS.docx --type SSS --tier large
```

## 编写目标

定义系统/子系统需求、外部接口、质量特性和鉴定检验方法。

## 首要来源材料

任务需求、总体技术要求、OCD、系统边界与外部接口、质量特性指标、鉴定检验方法。

## 基线关系

固定必选：OCD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/sss.yaml`。
