# Zcode 更新后的验收与返工

先在 Zcode 真正使用的 Python 环境更新核心包和 20 个入口。运行 `gjb438c --version`、`gjb438c doctor`，应显示 0.4.0、20 类 Profile 及随包母版。不要凭 SKILL.md 大小或时间戳判断。旧 `word-fillter-*` 不要铺到活动 Skill 目录。

在空临时目录运行 `gjb438c init --type SSS --output SSS.md`；不得传 template-root。再执行 review，初始骨架应失败。draft 可渲染为预览；review/release 失败不是工具坏了，而是内容仍不满足合同。预览不等于发布通过。

对已有 20 份 Markdown 原地复审，不重新生成平行文档集。工作基线使用 working-baselines；人工批准的文件另行登记。review PASS 不能自动复制进 approved-baselines。STR 没有实际执行数据时保持 draft；DBDD 真实表数不足只能由项目所有者批准适用性剪裁；FSM 没有自研固件不能批量伪造固件条目。

```bash
gjb438c audit docs/SSS.md --profile review --tier large --baseline-dir working-baselines --source-register sources/SSS-source-register.md --json reports/SSS-review.json
gjb438c suite-audit suite.yaml --profile review --json reports/suite-review.json
```

既有目录不是本工具初始化的套件时，先按 `suite-init` 在独立临时目录产生的 suite.yaml 格式建立清单；清单引用真实路径，不要覆盖原 docs。来源登记目前校验标识可解析和报告绑定，仍须人工逐条确认来源内容真正支撑结论。

每次只让一个 Agent 修改一份文件。大 SDD 先建立章节索引分段读；读取超限/429/超时后重试相关章节，不使用失败任务的“完成”摘要证明已读。报告所有未读章节及缺口。

正式 Word 只能在源文件批准后生成，并保留 `.content.json`、`.audit.json`、`.volume.json`。工具检测部分重复段落/证据，不保证识别所有换词凑数；项目内容的技术正确性和真实接口、DDL、测试步骤仍须评审。

单独改 Word 后不能沿用旧报告。import-word 产生候选 MD 后，人工对照结构化证据、图片和表格，再审计、批准、整体重发。字体替换或 Office 版本改变可能影响页数，目标交付环境必须再刷新和检查。
