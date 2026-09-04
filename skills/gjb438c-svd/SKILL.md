---
name: gjb438c-svd
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件版本说明（SVD、5.16、附录P）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SVD；Markdown 是评审基线，DOCX 是发布物。
---

# SVD · 软件版本说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SVD --project <project.yaml> --output docs/SVD.md
gjb438c audit docs/SVD.md --profile review
gjb438c render docs/SVD.md --output dist/SVD.docx --profile release --refresh-toc
gjb438c audit-docx dist/SVD.docx --profile release
gjb438c audit-volume dist/SVD.docx --type SVD --tier large
```

## 编写目标

说明一个发布版本的基线、变更、构建、兼容性、安装和已知问题。

## 首要来源材料

SPS、变更记录、构建流水线、兼容性矩阵、安装升级说明、已知问题与校验值。

## 基线关系

固定必选：SPS。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/svd.yaml`。
