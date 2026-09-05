---
name: gjb438c-srs
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件需求规格说明（SRS、5.10、附录J）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SRS；Markdown 是评审基线，DOCX 是发布物。
---

# SRS · 软件需求规格说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SRS --project <project.yaml> --output docs/SRS.md
gjb438c audit docs/SRS.md --profile review
gjb438c render docs/SRS.md --output dist/SRS.docx --profile release --refresh-toc
gjb438c audit-docx dist/SRS.docx --profile release
gjb438c audit-volume dist/SRS.docx --type SRS --tier large
```

## 编写目标

定义 CSCI 的完整、无歧义、可验证和可追踪需求。

## 首要来源材料

SSS/OCD/合同需求、用户场景、接口需求、性能与资源预算、质量特性、验收与验证依据。

## 基线关系

固定必选：无固定必选基线；至少提供其一：SSS, OCD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/srs.yaml`。
