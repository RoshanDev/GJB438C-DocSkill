---
name: gjb438c-sdsr
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件研制总结报告（SDSR、5.20、附录T）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SDSR；Markdown 是评审基线，DOCX 是发布物。
---

# SDSR · 软件研制总结报告

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SDSR --project <project.yaml> --output docs/SDSR.md
gjb438c audit docs/SDSR.md --profile review
gjb438c render docs/SDSR.md --output dist/SDSR.docx --profile release --refresh-toc
gjb438c audit-docx dist/SDSR.docx --profile release
gjb438c audit-volume dist/SDSR.docx --type SDSR --tier large
```

## 编写目标

总结研制结果、度量、重大问题、质量控制、保证活动和经验教训。

## 首要来源材料

SDP 与历次修订、需求/设计/测试基线、度量数据、重大问题闭环、质量保证记录、交付与版本清单。

## 基线关系

固定必选：SDP, STR, SVD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/sdsr.yaml`。
