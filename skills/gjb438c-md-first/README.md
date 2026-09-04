# gjb438c-md-first

覆盖 GJB 438C-2021 二十类文档的 Markdown-first 编写、内容审计、统一版式 DOCX 渲染与 Word 回流工具。

## 安装

```bash
python -m pip install -e '.[test]'
```

安装后使用统一命令 `gjb438c`。

## 命令

```text
gjb438c list
gjb438c init --type SRS --project examples/project.yaml --output docs/SRS.md
gjb438c audit docs/SRS.md --profile release
gjb438c audit docs/SDD.md --profile release --baseline-srs docs/SRS.md
gjb438c render docs/SDD.md --output dist/SDD.docx --profile release \
  --baseline-srs docs/SRS.md --refresh-toc
gjb438c refresh-toc dist/SDD.docx
gjb438c audit-docx dist/SDD.docx --profile release
gjb438c import-word dist/SDD-reviewed.docx --output docs/SDD-returned.md
```

## 目录

```text
gjb438c-md-first/
├── SKILL.md
├── config/
│   ├── front-matter.contract.yaml
│   └── style.json
├── docs/
├── examples/
│   ├── project.yaml
│   ├── SRS.example.md
│   └── SDD.example.md
├── gjb438c_suite/
│   ├── registry.py       # 20 类文档注册表
│   ├── markdown_doc.py   # Markdown 与 gjb-* 结构化块
│   ├── quality.py        # 内容门禁
│   ├── front_matter.py   # 统一前三页严格填写
│   ├── render.py         # Markdown→DOCX
│   ├── finalize.py       # TOC 缓存安全刷新
│   ├── audit_docx.py     # Word 格式审计
│   ├── import_word.py    # Word→Markdown
│   └── cli.py
├── templates/front-matter/standard-front-matter.docx
└── tests/
```

## 发布判定

一个 Word 文件只有同时满足以下条件才算通过本工具的发布门禁：

1. Markdown 内容审计通过；
2. 统一前三页结构与字段完整；
3. 可见目录缓存已经刷新；
4. 原生 TOC、PAGE 域和正文书签存在；
5. 标题、正文、图表题和表内文字样式符合锁定格式；
6. 不存在 `TODO`、`TBD`、`待补充`、`XXXX` 等占位内容；
7. SDD/SSDD 对已审核 SRS/SSS 的需求映射完整。
