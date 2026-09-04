# Markdown 与 Word 回流

## 生成时保存的基线

Markdown→DOCX 时，原始 Markdown 会经 gzip 压缩、Base64 编码并分块写入 `word/settings.xml` 的 `docVars`。同时记录：

- Markdown 源文件 SHA-256；
- `GJB_BODY` 书签内可见正文的归一化 SHA-256。

这些数据不会显示在正文，也不依赖本地绝对路径。

## 精确回流

运行：

```bash
gjb438c import-word dist/SDD.docx --output docs/SDD-returned.md
```

如果书签内可见正文哈希未变，工具直接恢复嵌入的原始 Markdown，结构化 `gjb-*` 数据块不会丢失。

## Word 中发生正文修改

可见正文变化后，工具不再声称“无损回流”。它会：

1. 读取原 front matter；
2. 从正文书签内提取标题、段落和表格；
3. 生成候选 Markdown；
4. 写入 `round_trip.exact: false` 和 `requires_review: true`；
5. 明确要求重新补齐并审核需求、设计、来源和追踪数据块。

文本框、浮动图形、复杂域、修订痕迹和 Word 特有布局不保证转成等价 Markdown。因此直接在 Word 中做大量语义修改后，必须重新执行 Markdown 内容审计，而不能只跑格式审计。
