# 吴语参考读音检索与质量分析工具

**Wu Dialect Reference Lookup & Quality Analytics**
`Python` · `Pandas` · `SQLite` · `OpenCC` · `Streamlit` · `Plotly` · `pytest`

基于公开 WikiHan IPA 语料独立开发的**方言参考读音查询辅助工具**，面向需要核对吴语参考读音的语料工作者。提供逐字检索、CSV 批量核查、多候选 IPA 提示、无参考读音清单、语料质量分析和**默认关闭**的本地开发测试指标。

> **独立作品声明：** 这不是腾讯标注平台的模块或替代品；不连接腾讯系统、不包含腾讯内部语料、员工数据或私有代码。仅用于展示公开数据处理与数据分析能力。

## 主要功能

| 模块 | 能做什么 | 对应技能 |
|---|---|---|
| 逐字参考读音检索 | 汉字/多字逐字查询、简繁兼容、IPA 候选展示、CSV 导出 | OpenCC, 参数化 SQL, 数据检索 |
| 批量 CSV 核查 | 1–500 行输入、无参考标记、多候选标记、优先核查清单 | Pandas, 数据标准化, 质量规则 |
| 统计口径对比 | 原始输入行覆盖率 vs 归一去重字形覆盖率 | 指标设计、去重、业务分析 |
| 语料质量看板 | 方言记录量、来源行填充率、吴语候选数分布 | SQL 聚合, Plotly |
| 本地产品指标（可选） | 测试搜索事件、零结果率、P50/P95 处理耗时 | SQLite 埋点, 分位数分析 |

**限制：** WikiHan 的 `Wu` 列对应上海话；不包含整词词条语料，不会把各字 IPA 拼接成“词语发音”。多个参考读音并非标注错误；没有匹配也不代表这个字在现实中没有读音。

## Mac / Python 3.13 启动

建议新建目录运行，不要在旧版 `app.py` 上继续逐段叠加代码。

```bash
cd ~/Downloads/wu_dialect_reference_tool
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

启动后打开 <http://localhost:8501>。初次运行自动建立 `data/processed/corpus.sqlite`，使用仓库内附带的少量 CC0 公开样例。

**下载完整 WikiHan 数据（推荐）：**

```bash
# 另开一个终端，进入同一个目录并激活 .venv
python scripts/fetch_wikihan.py
python scripts/build_database.py
python scripts/generate_report.py
```

刷新网站后将使用全量数据，`reports/tables/` 中有可复现的 SQL/Pandas 汇总输出。如下载失败，可从 [WikiHan 原始仓库](https://github.com/cmu-llab/wikihan) 手动取 `wikihan-ipa.tsv` 放入 `data/`。

**演示批量文件：** 页面提供下载，也可在 `data/demo_batch_queries.csv` 找到；列名为 `character`，每行一个字符（允许扩展汉字）。

## 本地测试

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m py_compile app.py src/*.py scripts/*.py
```

可选本地**开发测试**埋点（默认禁用，勿在公开云端启用）：

```bash
ENABLE_LOCAL_ANALYTICS=1 python -m streamlit run app.py
```

仅保存随机临时会话 ID、搜索类型、输入长度、结果数量、匹配方式数量和处理耗时；**不保存原文、上传内容、IP**。随机会话 ID 仍是**假名化标识**，不等于完全匿名。埋点仅用于本机开发测试，不代表真实用户、DAU 或改版提升。参考 `docs/PORTFOLIO_AND_PRIVACY.md`。

## 可复现项目结构

```text
wu_dialect_reference_tool/
├── app.py                        # 精简 Streamlit 前端
├── src/
│   ├── etl.py                    # TSV -> 规范化 SQLite
│   ├── analytics.py              # 参数化 SQL / 聚合分析
│   ├── lookup.py                 # 单一查询逻辑：逐字 + 批量共用
│   ├── metrics.py                # 覆盖率与核查优先级
│   ├── events.py                 # 默认关闭的本地开发埋点
│   └── config.py
├── scripts/
│   ├── fetch_wikihan.py
│   ├── build_database.py
│   └── generate_report.py
├── data/
│   ├── sample_wikihan.tsv       # WikiHan CC0 公开节选
│   ├── demo_batch_queries.csv
│   └── DATA_SOURCE.md
├── sql/analysis_queries.sql
├── docs/PORTFOLIO_AND_PRIVACY.md
├── tests/
├── .streamlit/config.toml
└── .github/workflows/ci.yml
```

## 数据与指标口径

- 单字查询：原字优先，未找到时尝试 OpenCC `s2t` 字形；结果来自 `readings` 表的真实 IPA，无 AI 猜测。
- `source_row` 是原始同源词条行号；数据库保留同一个字在不同同源词条中的行，避免词源信息丢失。
- **输入行覆盖率** = 有参考读音的有效输入行数 / 有效输入行数。
- **归一字形覆盖率** = 有参考读音的归一查询键数 / 归一查询键总数。
- **多候选核查** = 某归一字形返回 ≥2 条不同 IPA；只提示人工核对，不代表错误。
- **P50/P95** = 可选本地开发事件的服务端处理时间分位数，不包括端到端网络渲染。
- 简繁归一存在一简对多繁和语义歧义，不是严格的语义等价归并。

## GitHub 发布与安全

`.gitignore` 已排除 `.venv/`、原始全量 TSV、SQLite、events、`reports/`、密钥及缓存。**发布前仍需人工检查 `git status`，绝不提交任何内部或未经授权的数据**。

```bash
git init
git add .
git status
git commit -m "Initial public Wu reference lookup and analytics tool"
```

可将该项目描述为**独立个人项目**，与腾讯实习中真实开展的质检/抽检和方言资料查询经历分别书写；不可声称其在腾讯内部上线。简历示例和边界说明见 `docs/PORTFOLIO_AND_PRIVACY.md`。

## 来源与许可证

- 数据：WikiHan（上游 CC0） <https://github.com/cmu-llab/wikihan>
- 引用：Chang, K., Cui, C., Kim, Y., & Mortensen, D. R. (2022), *WikiHan: A New Comparative Dataset for Chinese Languages*, COLING.
- 本项目代码：MIT（`LICENSE`）；公开样本仍按上游 WikiHan CC0 许可处理。
- 吴语学堂 <https://www.wugniu.com/> 仅作参考网站，**未爬取、镜像或复制其数据库**。
