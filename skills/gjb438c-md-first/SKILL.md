---
name: gjb438c-md-first
description: 编写、修订、审核 GJB 438C-2021 的二十类文档，Markdown 到 Word、Word 受控回流、需求设计测试追踪。普通生成使用本核心及对应 gjb438c-xxx 入口；旧 word-fillter 仅供明确指定的兼容任务。
---

# GJB 438C Markdown-first（0.4.0）

先运行 `gjb438c --version`、`gjb438c doctor`、`gjb438c profile --type <TYPE>`，核对实际 Python、模块路径、20 个内置 Profile 和打包母版。不得只根据 Skill 文件大小判断版本。`init` 默认不需要 `--template-root`；该参数只是用户明确要求重新抽取外部模板时的可选覆盖。

## 执行合同

先登记可读材料的文件、版本、来源标识和定位信息；大文件分章节读取。读取失败、截断、子 Agent 超时后不能声称已覆盖全部来源。按依赖顺序分批生成，每份只有一个写入者；并发失败时保留工作清单再重试。

使用 `gjb438c init --type <TYPE> --project project.yaml --output docs/<TYPE>.md` 初始化；整套可用 `gjb438c-suite --project project.yaml --output workspace --tier large --min-body-pages 300`。既有工作区不重新初始化、不覆盖。20 份骨架不等于 20 份成品。

Markdown 保留 YAML front matter，使用本类型 Profile 的章节和 `gjb-*` 字段合同。按真实需求、设计、接口、数据和用例逐条展开。工程证据会在 Word 正文附录可见，不能用它替代正文的论证、步骤、字段表和图示。缺少事实只记录待提供项，不虚构接口、表、固件、性能、版本、测试结果或签字。

`draft` 允许待补材料并输出警告；`review` 检查当前规模的字段、数量、章节、正文字符和重复内容；`release` 再检查明确批准记录、上游基线、实际 Word 排版和发布集。机器 PASS 不是人工批准，目录名 baselines 也不是批准凭据。

审核人实际批准后，由项目所有者录入 `document.status: approved`、`approval.reviewer`、`approval.approved_at`，执行 `gjb438c fingerprint docs/<TYPE>.md` 将结果录入 `approval.content_sha256`。工具只校验声明完整性和内容绑定，不认证签署人的身份；Agent 不得自填批准。正文或元数据改变后旧批准失效。

数量不足不能凑数。按真实适用性提出 `gjb-tailoring`，字段为 id、target_kind、required_minimum、accepted_minimum、rationale、impact、source_refs、status、approved_by、approved_at；只有实际经批准且来源完整的记录才降低条目下限。没有自研固件时先做适用性决定，不把普通软件组件改名为固件。

## 命令顺序

```bash
gjb438c audit docs/SDD.md --profile review --tier large --baseline-dir working-baselines --json reports/SDD-review.json
# 只有人工批准及全部发布条件满足后，才执行 release：
gjb438c render docs/SDD.md --profile release --baseline-dir approved-baselines --output dist/SDD.docx --refresh-toc
gjb438c audit-docx dist/SDD.docx --profile release
gjb438c audit-volume dist/SDD.docx --source docs/SDD.md --type SDD --tier large
gjb438c suite-audit suite.yaml --profile release --json reports/suite.json
```

正式 render 自动产生 `SDD.docx.content.json`、`.audit.json`、`.volume.json`；全部暂存，报告先替换，DOCX 最后替换。异常返回非零，不发布新的半套文件。并发写入被锁阻止；进程被杀或断电后的锁/备份需人工恢复，不能直接删锁继续覆盖。多文件替换不是文件系统级原子快照，消费者仍须核验文件哈希。

Word 修改后先 `gjb438c import-word changed.docx --output candidate.md`；未变正文可精确回流，改过的正文只生成待人工对照的候选，撤销旧批准。不得宣称复杂图片、表格、修订或结构化证据编辑天然无损。目录刷新输出候选文件，不在已有正式发布集里单独覆盖 Word。

## 验收边界

页数由真实 Office 排版计算，排除前三页与目录；不能用 DOCX 页数元数据或字数估计。large 各类型门槛由 `volume-policy` 查询，项目可再提高；它们是工程策略，不是标准规定所有文件都必须若干页。禁止复制段落、空表、空白页或放大图片凑数。

前三页中性母版，真实组织信息仅留在用户项目数据，不进入公开仓库。目录标题三号宋体；目录与正文小四宋体 1.5 倍两端对齐；各级标题小四黑体；图表题五号黑体；表内五号宋体单倍；西文 Times New Roman。正式环境需可用字体和 LibreOffice/UNO；不同 Office/字体环境的分页差异必须重新核验。

自动检查不替代项目事实核验或人工逐页视觉验收。不得绕过核心自写生成器、删审计报告、降低规模、手改 passed 字段或把待测试 STR 宣称已通过。最终报告实际命令、退出码、文件哈希、未闭环项和真实页数；只在对应阶段确实通过时声称该阶段完成。
