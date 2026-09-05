---
name: gjb438c-dbdd
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 数据库设计说明（DBDD、5.12、附录L）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=DBDD；Markdown 是评审基线，DOCX 是发布物。
---

# DBDD · 数据库设计说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type DBDD --project <project.yaml> --output docs/DBDD.md
gjb438c audit docs/DBDD.md --profile review
gjb438c render docs/DBDD.md --output dist/DBDD.docx --profile release --refresh-toc
gjb438c audit-docx dist/DBDD.docx --profile release
gjb438c audit-volume dist/DBDD.docx --type DBDD --tier large
```

## 编写目标

描述数据库逻辑/物理模型、表、约束、索引、事务、安全和恢复。

## 首要来源材料

SDD/SSDD、数据字典、ER 模型、DDL、容量与性能预算、备份恢复与迁移方案。

## 基线关系

固定必选：无固定必选基线；至少提供其一：SDD, SSDD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/dbdd.yaml`。
