---
name: gjb438c-sip
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件安装计划（SIP、5.2、附录B）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SIP；Markdown 是评审基线，DOCX 是发布物。
---

# SIP · 软件安装计划

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SIP --project <project.yaml> --output docs/SIP.md
gjb438c audit docs/SIP.md --profile review
gjb438c render docs/SIP.md --output dist/SIP.docx --profile release --refresh-toc
gjb438c audit-docx dist/SIP.docx --profile release
gjb438c audit-volume dist/SIP.docx --type SIP --tier large
```

## 编写目标

策划用户现场的软件安装、转换、培训、验证和回退。

## 首要来源材料

产品规格与版本说明、现场调查记录、部署拓扑、安装脚本与配置、培训计划、回退方案。

## 基线关系

固定必选：SPS, SVD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/sip.yaml`。
