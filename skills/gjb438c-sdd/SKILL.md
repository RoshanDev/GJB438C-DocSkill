---
name: gjb438c-sdd
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件设计说明（SDD、5.11、附录K）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SDD；Markdown 是评审基线，DOCX 是发布物。
---

# SDD · 软件设计说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SDD --project <project.yaml> --output docs/SDD.md
gjb438c audit docs/SDD.md --profile review
gjb438c render docs/SDD.md --output dist/SDD.docx --profile release --refresh-toc
gjb438c audit-docx dist/SDD.docx --profile release
gjb438c audit-volume dist/SDD.docx --type SDD --tier large
```

## 编写目标

描述 CSCI 的设计决策、体系结构、设计单元、接口、数据和执行行为。

## 首要来源材料

已审核 SRS、架构决策记录、代码/模型、接口与数据模型、部署拓扑、异常与并发设计。

## 基线关系

固定必选：SRS。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/sdd.yaml`。
