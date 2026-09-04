---
name: gjb438c-strp
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件移交计划（STrP、5.3、附录C）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=STrP；Markdown 是评审基线，DOCX 是发布物。
---

# STrP · 软件移交计划

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type STrP --project <project.yaml> --output docs/STrP.md
gjb438c audit docs/STrP.md --profile review
gjb438c render docs/STrP.md --output dist/STrP.docx --profile release --refresh-toc
gjb438c audit-docx dist/STrP.docx --profile release
gjb438c audit-volume dist/STrP.docx --type STrP --tier large
```

## 编写目标

策划向保障机构移交软件产品、资源、知识和责任。

## 首要来源材料

交付清单、配置基线、保障资源清单、培训资料、知识转移计划、验收准则。

## 基线关系

固定必选：SPS, SVD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/strp.yaml`。
