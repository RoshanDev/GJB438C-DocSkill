---
name: gjb438c-str
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件测试报告（STR、5.14、附录N）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=STR；Markdown 是评审基线，DOCX 是发布物。
---

# STR · 软件测试报告

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type STR --project <project.yaml> --output docs/STR.md
gjb438c audit docs/STR.md --profile review
gjb438c render docs/STR.md --output dist/STR.docx --profile release --refresh-toc
gjb438c audit-docx dist/STR.docx --profile release
gjb438c audit-volume dist/STR.docx --type STR --tier large
```

## 编写目标

记录测试执行事实、结果、偏差、缺陷、覆盖和结论。

## 首要来源材料

STD、执行日志、测试证据、缺陷记录、覆盖率报告、偏差审批与复测记录。

## 基线关系

固定必选：STD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/str.yaml`。
