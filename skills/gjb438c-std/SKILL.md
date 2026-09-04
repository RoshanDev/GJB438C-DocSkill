---
name: gjb438c-std
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件测试说明（STD、5.13、附录M）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=STD；Markdown 是评审基线，DOCX 是发布物。
---

# STD · 软件测试说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type STD --project <project.yaml> --output docs/STD.md
gjb438c audit docs/STD.md --profile review
gjb438c render docs/STD.md --output dist/STD.docx --profile release --refresh-toc
gjb438c audit-docx dist/STD.docx --profile release
gjb438c audit-volume dist/STD.docx --type STD --tier large
```

## 编写目标

规定每个测试用例的设置、数据、步骤、检查点、判据和追踪。

## 首要来源材料

STP、需求基线、接口需求、环境配置、测试数据、自动化脚本与判据。

## 基线关系

固定必选：STP；至少提供其一：SRS, SSS。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/std.yaml`。
