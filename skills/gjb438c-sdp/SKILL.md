---
name: gjb438c-sdp
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件开发计划（SDP、5.1、附录A）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SDP；Markdown 是评审基线，DOCX 是发布物。
---

# SDP · 软件开发计划

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SDP --project <project.yaml> --output docs/SDP.md
gjb438c audit docs/SDP.md --profile review
gjb438c render docs/SDP.md --output dist/SDP.docx --profile release --refresh-toc
gjb438c audit-docx dist/SDP.docx --profile release
gjb438c audit-volume dist/SDP.docx --type SDP --tier large
```

## 编写目标

策划并控制软件开发全过程、方法、资源、进度、风险和保证活动。

## 首要来源材料

合同/技术协议、生存周期模型、WBS 与里程碑、组织和资源计划、风险清单、保证与配置管理制度。

## 基线关系

固定必选：无固定必选基线。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/sdp.yaml`。
