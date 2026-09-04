---
name: gjb438c-ocd
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 运行方案说明（OCD、5.5、附录E）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=OCD；Markdown 是评审基线，DOCX 是发布物。
---

# OCD · 运行方案说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type OCD --project <project.yaml> --output docs/OCD.md
gjb438c audit docs/OCD.md --profile review
gjb438c render docs/OCD.md --output dist/OCD.docx --profile release --refresh-toc
gjb438c audit-docx dist/OCD.docx --profile release
gjb438c audit-volume dist/OCD.docx --type OCD --tier large
```

## 编写目标

描述用户需要、运行环境、使用方式、任务场景和与现有系统的关系。

## 首要来源材料

用户访谈、任务流程、运行规程、现有系统资料、典型/异常/降级场景、环境约束。

## 基线关系

固定必选：无固定必选基线。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/ocd.yaml`。
