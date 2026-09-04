# GJB438C-DocSkill

面向 GJB 438C-2021 软件生命周期文档的 Markdown-first 编写、审查、DOCX 生成与回流工具集。

## 当前能力

- 覆盖 SDP、SIP、STrP、STP、OCD、SSS、IRS、SSDD、IDD、SRS、SDD、DBDD、STD、STR、SPS、SVD、SUM、CPM、FSM、SDSR 共 20 类文档；
- 从仓库 DOCX 模板提取章节骨架，Markdown 作为评审阶段的内容真相源；
- SRS 需求可验证性、来源、验收准则与追踪门禁；
- SDD 架构决策、设计单元、接口、数据、场景、部署、安全、验证与 SRS 覆盖门禁；
- Markdown → DOCX、DOCX 格式审计、Word → Markdown 候选回流；
- 可替换的统一首页、签字页、变更履历三页母版；
- 目录标题、正文、各级标题、图表题、表内文字与西文字体的固定格式检查。

## 快速开始

```bash
python -m pip install -e 'skills/gjb438c-md-first[test]'

gjb438c list
gjb438c init --type SRS --project skills/gjb438c-md-first/examples/project.yaml --output docs/SRS.md
gjb438c audit docs/SRS.md --profile review
gjb438c render docs/SRS.md --output dist/SRS.docx --profile release --refresh-toc
gjb438c audit-docx dist/SRS.docx --profile release
```

SDD 发布审查应绑定已经审核的 SRS：

```bash
gjb438c audit docs/SDD.md --profile release --baseline-srs docs/SRS.md
```

详细说明见 [`skills/gjb438c-md-first/README.md`](skills/gjb438c-md-first/README.md)。旧的 SRS/SDD Word 填充入口暂时保留，用于兼容和回归对照。

## 公开仓库安全

示例、文档、测试和模板不得包含真实单位名称、项目代号、人员信息、IP 地址、内部拓扑或其他项目特定标识。统一前三页母版使用中性锚点 `编制单位`，实际单位名称仅在用户本地项目数据中填入，不应提交到本仓库。

## 许可证与来源

本仓库沿用原项目许可证。第三方参考与改造说明见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
