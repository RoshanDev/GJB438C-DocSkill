# GJB438C-DocSkill

GJB 438C-2021 二十类文档的 Markdown-first 工具链。默认安装 `skills/` 下 1 个核心和 20 个文档入口；兼容填充器在 `legacy-skills/`，不进入默认发现目录。

## 安装与确认

在仓库根目录运行：

```bash
python -m pip install --upgrade './skills/gjb438c-md-first'
gjb438c --version
gjb438c doctor
gjb438c list
```

本版本为 **0.4.0**。Windows、WSL、Hermes venv 必须在实际执行 Zcode 的同一个 Python 环境更新。Skill 文本同步和 Python 包更新是两件事；`doctor` 输出实际解释器、运行模块、Profile 和母版路径。仅更新符号链接不代表 CLI 更新。只安装核心目录或 wheel 也可初始化全部 20 类，日常不需要根目录 DOCX 模板包。

## 工作流

```bash
gjb438c init --type OCD --project project.yaml --output docs/OCD.md
gjb438c audit docs/OCD.md --profile draft --json reports/OCD-draft.json
# 完善正文及证据后：
gjb438c audit docs/OCD.md --profile review --tier large --json reports/OCD-review.json
# 整套新工作区，可采用项目自定 300 正文页下限：
gjb438c-suite --project project.yaml --output new-workspace --tier large --min-body-pages 300
```

默认文档类型：SDP、SIP、STrP、STP、OCD、SSS、IRS、SSDD、IDD、SRS、SDD、DBDD、STD、STR、SPS、SVD、SUM、CPM、FSM、SDSR。每类有自己的章节与字段合同；MD 与 DOCX 是同一文档的源和发布格式，不是两套 Skill。

生产发布使用 `render --profile release --baseline-dir approved-baselines`，会自动产生 DOCX、内容报告、格式报告和体量报告。只有全部验证成功才提交发布集；失败时保留旧文件。`--profile=release`、重复参数等形式均由同一个 argparse 解析器处理，不存在保护层和实际执行层不一致的第二套解析。

`review` 不等于人工批准，自动工具不认证审核人身份。批准需项目所有者真实确认并录入内容指纹；变更使旧批准失效。来源标识存在只证明引用能解析，不证明材料结论真实。人工语义评审、字体环境和逐页版式验收仍是交付必需项。

## 测试

```bash
python -m pip install -e './skills/gjb438c-md-first[test]'
python -m pytest skills/gjb438c-md-first/tests
python tools/check_wheel.py
# 已安装 LibreOffice/UNO 时：
GJB_OFFICE_TESTS=1 python -m pytest skills/gjb438c-md-first/tests/test_office_integration.py
python tools/stress_volume_gate.py
```

300 页样本仅验证排版和重复检测，不是正式项目内容。模板和注册表完整不代表任意生成结果达到评审质量。详见核心 `SKILL.md` 与 `docs/ZCODE-HANDOFF.md`。

## 维护约束

运行时和测试必须直接提交。CI 只校验当前源码，不生成后再推回实现；不得提交 bootstrap 分片、自修改工作流或以“稍后会生成”为理由合并。新的修复提交必须重新通过当前 head 的 CI 与 Codex review，不能复用旧提交的审查结果。公开仓库禁止真实组织标识、项目材料、内部拓扑和秘密。
