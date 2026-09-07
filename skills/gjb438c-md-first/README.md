# GJB 438C Markdown-first 0.4.0

本目录是可独立安装的 Python 包及 Agent Skill。默认使用随包的二十类 Profile 和中性前三页 DOCX 母版，无需仓库根模板目录。

```bash
python -m pip install --upgrade .
gjb438c --version
gjb438c doctor
gjb438c list
gjb438c init --type OCD --output docs/OCD.md
```

完整工作流、限制、格式和人工批准要求见同目录 `SKILL.md`。普通生成只使用核心与对应 `gjb438c-xxx` 薄入口，不使用旧 `word-fillter-*`。

正式 `render --profile release` 完成内容、基线、格式、目录和真实页数审计后，才提交 DOCX 与三份 JSON 报告。审计失败不覆盖旧发布集。发布集替换并非多文件全局原子快照；消费者须核验哈希，进程终止后需人工检查遗留锁和备份。

`review` 只表示机器规则结果，不代表来源事实成立或人工批准。初始骨架应通过 draft 而不应通过 review/release。工具不生成真实签字、不虚构测试结果、不凭页数证明内容质量。
