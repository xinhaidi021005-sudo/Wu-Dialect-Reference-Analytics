# Portfolio positioning & privacy

## What the project is

**An independently developed Wu pronunciation reference lookup and quality analytics assistant.** It may help people doing dialect annotation/review find public reference IPA faster and flag ambiguous entries. It is **not** an employee labeling platform and does not perform labeling, quality-control decisions, or automatic transcript validation.

## What it is not

- Not a Tencent project, Tencent-internal product, integration, or codebase.
- Not connected to the Tencent annotation platform or internal datasets.
- Not a whole-word pronunciation or translation engine.
- Not an AI inference/LLM-powered retrieval system. AI-assisted coding is not equivalent to deployed AI inference.
- Not a production-grade employee tracking or privacy-compliant telemetry platform.

## Privacy-by-design for the public repo

- Bundle only CC0 sample corpus and synthetic *inputs* (not invented pronunciations).
- `.gitignore` excludes full dataset, SQLite corpora/event DBs, cache, secrets, and local exports.
- Uploaded CSV inputs are processed in the current Streamlit process/session and are **not logged**. Downloaded results may contain the user-provided input; share exports only if permitted. CSV export neutralizes cells starting with spreadsheet formula markers.
- Optional telemetry defaults **OFF**. `ENABLE_LOCAL_ANALYTICS=1` records only developer test events, random per-session IDs, types, counts, and local processing duration; never store search text, IP address, or CSV content.
- The session ID is *pseudonymous*, not proof of anonymization. Public hosting should keep telemetry OFF pending access controls, notice/consent where necessary, retention policy, and a persistent secured event store.
- Avoid uploading/processing confidential corporate data on public Streamlit deployments.

## Suggested verified resume description (personal project, not internship output)

> 吴语参考读音检索与质量分析工具｜独立个人项目（公开 WikiHan 数据）：使用 Python/Pandas 完成语料清洗及多候选 IPA 展开，采用 SQLite 参数化查询和 OpenCC 实现简繁兼容的逐字/批量参考检索；设计输入行与归一去重字形两种覆盖率口径，自动归类无参考、多候选情况并导出核查清单；使用 Plotly/Streamlit 展示语料质量与本地测试检索表现。

### How to discuss the Tencent internship separately

Describe **only work actually performed**, such as your participation in annotation spot checks/quality reviews, reference queries, dialect data processing, and audio recording if those tasks are true. Then explain that you **independently built** this public-data portfolio project to demonstrate Python, SQL, analytics, and domain understanding. Never claim that Tencent deployed or used this project, or that you exported company data.

## Example with the included six-row demo

Input characters: 车, 马, 車, 馬, 月, 𪚥.

If the fetched corpus yields the same matches as the verified example: row coverage 5/6 (83.33%); normalized search-key coverage 3/4 (75%). These are **development fixture** results, not benchmarked improvement percentages.

## Further improvements worth measuring

- Measure repeatable latency over enough trials before stating performance numbers.
- Add baseline-vs-normalized retrieval comparisons on a fixed CC0-only test set; report fixed denominators and failure categories.
- Review 1-to-many simplified/traditional glyph mappings and mismatches manually rather than silently merging meanings.
