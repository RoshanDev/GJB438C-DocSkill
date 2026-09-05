---
name: gjb438c-ssdd
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 系统/子系统设计说明（SSDD、5.8、附录H）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SSDD；Markdown 是评审基线，DOCX 是发布物。
---

# SSDD · 系统/子系统设计说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SSDD --project <project.yaml> --output docs/SSDD.md
gjb438c audit docs/SSDD.md --profile review
gjb438c render docs/SSDD.md --output dist/SSDD.docx --profile release --refresh-toc
gjb438c audit-docx dist/SSDD.docx --profile release
gjb438c audit-volume dist/SSDD.docx --type SSDD --tier large
```

## 编写目标

描述系统/子系统级设计决策、体系结构、执行方案和分配关系。

## 首要来源材料

SSS 基线、架构决策记录、系统分解、硬软件分配、接口与数据设计、部署与执行模型。

## 基线关系

固定必选：SSS。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/ssdd.yaml`。
