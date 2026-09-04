---
name: gjb438c-sps
description: 当用户明确要求按 GJB 438C-2021 编制、修订、审核或导出 软件产品规格说明（SPS、5.15、附录O）时使用。该入口调用共享核心 gjb438c-md-first，并固定 document.type=SPS；Markdown 是评审基线，DOCX 是发布物。
---

# SPS · 软件产品规格说明

这是 `gjb438c-md-first` 的薄路由入口，不复制渲染器、审计器或模板。

## 固定调用

```bash
gjb438c init --type SPS --project <project.yaml> --output docs/SPS.md
gjb438c audit docs/SPS.md --profile review
gjb438c render docs/SPS.md --output dist/SPS.docx --profile release --refresh-toc
gjb438c audit-docx dist/SPS.docx --profile release
gjb438c audit-volume dist/SPS.docx --type SPS --tier large
```

## 编写目标

精确定义可交付软件产品、组成、构建、配置、安装、运行和完整性。

## 首要来源材料

构建产物、SBOM/依赖、配置基线、安装与运行信息、完整性校验、限制条件。

## 基线关系

固定必选：无固定必选基线；至少提供其一：SDD, SSDD。实际剪裁必须记录理由，不得用页数或套话替代缺失证据。

## 发布原则

- 默认使用 `large` 规模档位；`prototype` 仅用于冒烟，禁止作为正式交付。
- 页数只是防止空壳的下限之一；还必须通过条目数量、来源、追踪、正文密度、薄页率和重复页率检查。
- 不得编造项目事实、测试结果、接口、性能、兼容性或签字信息。
- 详细字段合同和章节结构读取共享核心内置 Profile：`gjb438c_suite/data/profiles/sps.yaml`。
