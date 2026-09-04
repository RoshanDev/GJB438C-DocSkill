# GJB 438C Markdown-first 文档工程

本仓库在原有 SRS 严格填充能力之上，建立一条覆盖 GJB 438C-2021 二十类文档的可审计生产线：

```text
项目资料 / 既有文档 / 代码 / 接口 / 数据模型
                  ↓
              Markdown 基线
                  ↓
       内容审查 + 来源证据 + 追踪门禁
                  ↓
         统一前三页 + Word 正文
                  ↓
      DOCX 结构、字体、字段与视觉验收
```

核心代码位于 [`skills/gjb438c-md-first/`](skills/gjb438c-md-first/)。原有
`word-fillter-438c-srs` 和 `word-fillter-438c-sdd` 暂时保留，用于兼容旧流程和回归对照。

## 当前能力

- 覆盖 `SDP / SIP / STrP / STP / OCD / SSS / IRS / SSDD / IDD / SRS / SDD / DBDD / STD / STR / SPS / SVD / SUM / CPM / FSM / SDSR` 二十类文档。
- 以仓库中对应 DOCX 模板的真实目录为章节结构基线，不让模型凭记忆编造目录。
- 评审阶段以 Markdown 为内容真相源；发布时生成 DOCX。
- 使用统一首页、签字页、变更履历三页母版。
- 支持 SRS 需求质量门禁和 SRS→SDD 需求覆盖门禁。
- 生成原生 Word `TOC`、`PAGE` 域以及正文书签。
- 可将 Word 修改回流为 Markdown；正文未改时精确恢复嵌入基线，正文已改时生成必须复审的候选稿。
- 对 DOCX 的字体、字号、行距、样式、页码域、目录域、前三页结构和占位符进行自动审计。

## 统一版式基线

| 角色 | 格式 |
|---|---|
| 首页、签字页、变更履历 | 采用本仓库归一化后的统一三页母版 |
| 目录标题 | 三号宋体，1.5 倍行距，居中 |
| 目录文字 | 小四宋体，1.5 倍行距，两端对齐 |
| 各级标题 | 小四黑体，1.5 倍行距 |
| 正文 | 小四宋体，1.5 倍行距，两端对齐 |
| 图名、表名 | 五号黑体，单倍行距，居中 |
| 表内文字 | 五号宋体，单倍行距 |
| 西文 | Times New Roman |

用户提供的前置页版式文件被用作前三页的权威版式来源。归一化过程中只做了母版化所需的处理：截断后续目录和正文、稳定三页分页、把原先在兼容渲染器中溢到签字页顶部的封面日期放回首页、清理个人文档元数据。未重画封面，也未用通用模板替代原始统一版式。

## 快速开始

```bash
python -m pip install -e 'skills/gjb438c-md-first[test]'

# 查看二十类文档
GJB438C_ROOT=skills/gjb438c-md-first
gjb438c list

# 从对应的真实模板目录生成 Markdown 骨架
gjb438c init \
  --type SDD \
  --project "$GJB438C_ROOT/examples/project.yaml" \
  --output docs/SDD.md

# 内容审核：SDD 必须绑定已经审核的 SRS
gjb438c audit docs/SRS.md --profile release
gjb438c audit docs/SDD.md --profile release --baseline-srs docs/SRS.md

# 生成最终 Word，并刷新可见目录缓存
gjb438c render docs/SDD.md \
  --output dist/SDD.docx \
  --profile release \
  --baseline-srs docs/SRS.md \
  --refresh-toc \
  --docx-audit-json dist/SDD.audit.json
```

`--refresh-toc` 需要 LibreOffice。它只借助 LibreOffice 计算目录内容和页码，随后仅将 TOC 的缓存结果回填到原 DOCX；不会采用 LibreOffice 重写后的整份文档，从而避免节、样式或自定义属性漂移。未安装 LibreOffice 时，仍可生成带真实 TOC 域的文档，打开 Word/WPS 后全选并按 `F9` 更新域。

## 两种后续返工方式

### Markdown 继续作为基线

修改 `.md`，重新执行 `audit → render --refresh-toc → audit-docx`。这是默认推荐路径，因为需求、设计单元、来源和追踪关系可以继续自动验证。

### 直接在 Word 中修改

少量措辞、表宽、图片位置、签字和发布性排版可以直接在 Word/WPS 中完成。修改后执行：

```bash
gjb438c audit-docx dist/SDD-reviewed.docx --profile release
```

需要重新进入 Markdown 流程时：

```bash
gjb438c import-word dist/SDD-reviewed.docx --output docs/SDD-returned.md
```

如果可见正文未改变，会精确恢复生成时嵌入的 Markdown；如果正文已改变，会输出候选 Markdown，并强制标记 `requires_review: true`，不能把丢失的结构化证据当作已审核内容。

## 质量门禁

SRS 的每条结构化需求至少包含稳定标识、规范性陈述、理由、来源、优先级、验证方法和可判定的验收准则。SDD 则要求设计决策、总体架构、设计单元、接口、数据、关键场景、部署、安全、验证和追踪证据，并计算已审核 SRS 的需求覆盖率。发布配置下，未覆盖需求、越界需求引用、无来源设计结论、占位内容和空证据块都会阻断。

详见：

- [`skills/gjb438c-md-first/README.md`](skills/gjb438c-md-first/README.md)
- [`skills/gjb438c-md-first/docs/CONTENT-CONTRACT.md`](skills/gjb438c-md-first/docs/CONTENT-CONTRACT.md)
- [`skills/gjb438c-md-first/docs/WORD-FORMAT.md`](skills/gjb438c-md-first/docs/WORD-FORMAT.md)
- [`skills/gjb438c-md-first/docs/ROUND-TRIP.md`](skills/gjb438c-md-first/docs/ROUND-TRIP.md)
- [`VERIFICATION.md`](VERIFICATION.md)

## 来源与许可证

本仓库以 `CMoments/GJB438C-DocSkill` 为起点，并参考公开的格式审计、文档处理和知识工程项目。具体归属和边界见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。本实现不会把参考项目的宣传指标当作本仓库的验证结果，也不会把仓库自定义质量门禁冒充为标准逐字条款。
