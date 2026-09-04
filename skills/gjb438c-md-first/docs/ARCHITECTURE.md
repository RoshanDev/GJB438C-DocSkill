# 实现架构

```text
registry.py
  └─ 二十类文档、模板文件名、工程证据底线

markdown_doc.py
  ├─ YAML front matter
  ├─ Markdown 标题/表格/图片解析
  ├─ gjb-* YAML 证据块
  └─ 从真实 DOCX 模板抽取目录骨架

quality.py
  ├─ 通用元数据/来源/占位符审计
  ├─ SRS 需求可验证性
  ├─ SDD 设计完整性
  └─ SRS→SDD 覆盖率与越界引用

front_matter.py
  └─ 统一前三页严格定位、填写和结构审计

render.py
  ├─ 独立 GJB 样式集
  ├─ Markdown→Word 正文
  ├─ TOC/PAGE 域和正文书签
  └─ 嵌入 Markdown 回流基线

finalize.py
  └─ LibreOffice 计算 TOC，安全移植缓存结果

audit_docx.py
  └─ OOXML 字段、节、字体、字号、行距、样式和占位符审计

import_word.py
  ├─ 精确恢复嵌入 Markdown
  └─ Word 已改时生成必须复审的候选 Markdown
```

设计上刻意避免把大模型调用、向量数据库、知识图谱或 Web 服务设为生成文档的强制依赖。资料检索和 AI 编写可以在上层完成，底层格式、结构、证据和追踪检查应能在离线环境以确定性 Python 工具运行。
