---
name: gjb438c-cpm
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 计算机编程手册（CPM、5.18、附录R）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=CPM；Markdown 是评审基线，DOCX 是发布物。
---

# CPM · 计算机编程手册

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type CPM --project <project.yaml> --output docs/CPM.md
gjb438c audit docs/CPM.md --profile review
gjb438c render docs/CPM.md --output dist/CPM.docx --profile release --refresh-toc
gjb438c audit-docx dist/CPM.docx --profile release
gjb438c audit-volume dist/CPM.docx --type CPM --tier large
```

## 编写目标

面向维护开发人员说明代码组织、构建、编码约定、API、并发和测试。

## 首要来源材料

SDD/代码仓库、构建脚本、编码规范、API 文档、数据模型、测试和维护指南。

## 基线关系

固定必选：无固定必选基线；至少提供其一：SDD, SSDD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/cpm.yaml`。
