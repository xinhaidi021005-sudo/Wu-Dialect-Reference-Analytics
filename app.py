"""Independent public-data reference tool; not connected to an employer platform."""
from __future__ import annotations

from contextlib import closing
from html import escape
from time import perf_counter
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics import (
    compare, connect, dialect_coverage, kpis, quality_coverage,
    quality_metadata, query_readings, wu_multiple_readings,
)
from src.config import (
    CORPUS_DB, EVENT_DB, FULL_DATA, SAMPLE_DATA, LOCAL_ANALYTICS_ENABLED,
)
from src.etl import DIALECTS, DISPLAY_NAMES, build_database
from src.events import daily_events, load_events, log_event, summarize_events
from src.lookup import audit_characters
from src.metrics import analyze_batch, category_counts

st.set_page_config(page_title="吴语参考读音检索与质量分析", page_icon="🔎", layout="wide")


def source_and_database():
    source = FULL_DATA if FULL_DATA.is_file() else SAMPLE_DATA
    if not source.exists():
        st.error("找不到 WikiHan 样例文件。请重新解压完整项目。")
        st.stop()
    if not CORPUS_DB.exists() or CORPUS_DB.stat().st_mtime < source.stat().st_mtime:
        with st.spinner("正在清洗公开语料并建立 SQLite 检索索引……"):
            build_database(source, CORPUS_DB)
    return source


def make_csv(df: pd.DataFrame) -> bytes:
    """Excel-friendly CSV; neutralize spreadsheet formulas from untrusted inputs."""
    safe = df.copy()
    for col in safe.select_dtypes(include=["object", "string"]).columns:
        safe[col] = safe[col].map(
            lambda v: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v
        )
    return safe.to_csv(index=False).encode("utf-8-sig")


def clear_batch_result():
    st.session_state.pop("batch_result", None)


def local_event(event_name, count, matched, search_type, elapsed_ms=None, exact=None, converted=None):
    if LOCAL_ANALYTICS_ENABLED:
        log_event(
            EVENT_DB, st.session_state["local_session_id"], event_name,
            count, matched, search_type=search_type,
            duration_ms=elapsed_ms, exact_match_count=exact,
            converted_match_count=converted,
        )


def record_export(search_type: str, total: int, matched: int):
    """Record a click event, never export file content."""
    local_event("export", total, matched, search_type)


@st.cache_data(show_spinner=False)
def load_corpus_quality(db_mtime: float):
    # db_mtime invalidates cached aggregate SQL when the source is replaced.
    with closing(connect(CORPUS_DB)) as conn:
        summary = kpis(conn)
        cov = dialect_coverage(conn)
        filled = quality_coverage(conn)
        metadata = quality_metadata(conn)
        multiple = wu_multiple_readings(conn, limit=30)
        candidate_counts = pd.read_sql_query("""
            SELECT distinct_ipa, COUNT(*) AS characters FROM (
                SELECT character, COUNT(DISTINCT ipa) AS distinct_ipa
                FROM readings WHERE dialect='Wu' GROUP BY character
            ) GROUP BY distinct_ipa ORDER BY distinct_ipa
        """, conn)
    return summary, cov, filled, metadata, multiple, candidate_counts


source_file = source_and_database()
if "local_session_id" not in st.session_state:
    st.session_state["local_session_id"] = uuid.uuid4().hex
if "lookup_result" not in st.session_state:
    st.session_state["lookup_result"] = None

summary, coverage, quality, meta, multi, candidate_freq = load_corpus_quality(CORPUS_DB.stat().st_mtime)

st.title("吴语参考读音检索与质量分析")
st.caption("Independent Wu Reference Lookup & Quality Analytics  |  Python · SQL · Pandas · OpenCC · Streamlit · Plotly")
if source_file == SAMPLE_DATA:
    st.warning("当前使用公开 WikiHan 小样本，仅用于功能演示。运行 `python scripts/fetch_wikihan.py` 后可切换至全量数据。")
else:
    st.success("已加载公开 WikiHan IPA 全量数据。Wu 列对应上海话数据，不代表所有吴语方言。")

with st.sidebar:
    st.header("工具说明")
    st.write("用途：**为方言语料核查人员提供参考读音查询和数据质量分析**。")
    st.caption("本项目独立构建，不接入腾讯或其他公司的内部标注系统，不使用企业私有语料。")
    st.link_button("WikiHan 数据来源", "https://github.com/cmu-llab/wikihan")
    st.caption(f"当前源文件：{source_file.name}（WikiHan / CC0）")
    st.caption("Wu = WikiHan 的上海话数据；多个候选 IPA 并非标注错误。")
    if LOCAL_ANALYTICS_ENABLED:
        st.info("本地开发埋点已启用。仅保存随机会话标识与聚合字段，不保存搜索文字；仅供开发测试。")
    else:
        st.caption("本地行为埋点默认关闭。输入的查询及上传的 CSV 不写入事件数据库。")

x1, x2, x3 = st.columns(3)
x1.metric("吴语参考字形数", f"{summary['wu_characters']:,}")
x2.metric("吴语 IPA 记录", f"{summary['wu_readings']:,}")
x3.metric("吴语多候选字形数", f"{summary['wu_multiple_characters']:,}")
st.caption("以上指标是当前参考语料的记录统计，不是实际语言人口覆盖率。")

search_tab, batch_tab, quality_tab, events_tab = st.tabs([
    "🔎 逐字参考检索", "📄 批量 CSV 核查", "📊 语料质量分析", "📈 本地产品指标",
])

with search_tab:
    st.subheader("输入单字或多个汉字")
    st.caption("按顺序逐字查找参考 IPA。**不是整词读音推断、翻译或语音合成。**")
    with st.form("char_search_form"):
        left, right = st.columns([3, 2])
        with left:
            phrase = st.text_input("汉字", placeholder="例如：车马 / 車馬 / 月", max_chars=12)
        with right:
            dialect = st.selectbox("参考方言", DIALECTS, format_func=lambda d: DISPLAY_NAMES[d], index=0)
        submitted = st.form_submit_button("查询参考读音", type="primary")

    if submitted:
        chars = [char for char in phrase if not char.isspace()]
        if not chars:
            st.warning("请输入要检索的汉字。")
        else:
            start = perf_counter()
            result = audit_characters(pd.DataFrame({"character": chars}), CORPUS_DB, dialect=dialect, max_rows=12)
            elapsed_ms = (perf_counter() - start) * 1000
            st.session_state["lookup_result"] = result
            st.session_state["lookup_meta"] = {"dialect": dialect, "elapsed_ms": elapsed_ms}
            local_event(
                "search", len(chars), int(result["match_method"].isin(["exact", "converted"]).sum()),
                "character", elapsed_ms=elapsed_ms,
                exact=int((result["match_method"] == "exact").sum()),
                converted=int((result["match_method"] == "converted").sum()),
            )

    result = st.session_state.get("lookup_result")
    if result is not None:
        if st.session_state["lookup_meta"]["dialect"] != dialect:
            st.warning("方言选择已改变：当前展示的是上次查询结果，请重新提交查询。")
        st.markdown("#### 逐字参考结果")
        for i, row in result.iterrows():
            with st.container(border=True):
                char_col, info_col = st.columns([1, 4])
                with char_col:
                    char = row["input_character"]
                    st.markdown(
                        '<div style="font-family:PingFang SC,Hiragino Sans GB,Arial,sans-serif;'
                        'font-size:40px;line-height:1.7;word-break:break-all">'
                        + escape(char) + '</div>', unsafe_allow_html=True,
                    )
                    st.caption(" ".join(f"U+{ord(ch):04X}" for ch in char))
                with info_col:
                    if row["match_method"] in {"exact", "converted"}:
                        st.markdown("**参考 IPA：** " + row["reference_ipa"])
                        method = "原字匹配" if row["match_method"] == "exact" else "简繁转换匹配"
                        st.caption(f"匹配字形：{row['matched_character']} · {method} · {int(row['candidate_count'])} 个不同候选读音")
                        if row["candidate_count"] > 1:
                            st.info("存在多个参考候选读音，请结合实际标注上下文核查。")
                    else:
                        st.warning("当前参考语料无对应读音" if row["match_method"] == "not_found" else "非单个字符，无法检索")
                        st.caption("无参考值不表示汉字不存在或人工标注错误。")
        with st.expander("查看结构化数据"):
            st.dataframe(result, hide_index=True, width="stretch")
        st.download_button(
            "下载本次检索 CSV", make_csv(result), "wu_reference_lookup.csv", "text/csv",
            key="download_single_result",
            on_click=record_export if LOCAL_ANALYTICS_ENABLED else "ignore",
            args=("character", len(result), int(result["match_method"].isin(["exact", "converted"]).sum())),
        )
        m = st.session_state["lookup_meta"]
        st.caption(f"查询处理耗时约 {m['elapsed_ms']:.1f} ms（含 Python 处理和 SQLite 查询，不含浏览器渲染）。")

    with st.expander("高级查询：汉字或 IPA 子串检索"):
        with st.form("ipa_form"):
            q = st.text_input("字形 / IPA 片段", placeholder="例如：車 或 ˥˧", max_chars=60)
            scope = st.selectbox("方言范围", ["全部"] + DIALECTS, format_func=lambda v: DISPLAY_NAMES.get(v, v))
            submitted_ipa = st.form_submit_button("高级检索")
        if submitted_ipa:
            if not q.strip():
                st.info("请输入查询内容。")
            else:
                start = perf_counter()
                with closing(connect(CORPUS_DB)) as conn:
                    ipa_df = query_readings(conn, q, dialect=scope)
                elapsed = (perf_counter() - start) * 1000
                st.dataframe(ipa_df, hide_index=True, width="stretch")
                st.caption("最多展示 500 条记录；此功能是字形/IPA 字符串检索，不是语义问答。")
                local_event("search", len(q), len(ipa_df), "ipa", elapsed_ms=elapsed)
                if not ipa_df.empty:
                    st.download_button("下载高级检索结果 CSV", make_csv(ipa_df), "ipa_lookup.csv", "text/csv", key="download_ipa",
                        on_click=record_export if LOCAL_ANALYTICS_ENABLED else "ignore",
                        args=("ipa", len(q), len(ipa_df)))

with batch_tab:
    st.subheader("批量参考读音核查")
    st.caption("上传 UTF-8 CSV，要求一列名为 `character`，每行一个字，最多 500 行；上传数据只在当前会话内处理。")
    st.download_button(
        "下载演示 CSV", (source_file.parent / "demo_batch_queries.csv").read_bytes(),
        "demo_batch_queries.csv", "text/csv", key="download_demo", on_click="ignore",
    )
    uploaded_file = st.file_uploader(
        "上传汉字清单", type="csv", key="batch_csv", on_change=clear_batch_result,
    )
    batch_dialect = st.selectbox("核查方言", DIALECTS, format_func=lambda d: DISPLAY_NAMES[d], key="batch_dialect")
    if st.button("开始批量核查", key="run_batch", type="primary"):
        if uploaded_file is None:
            st.warning("请先选择 CSV 文件。")
        elif uploaded_file.size > 1_000_000:
            st.error("文件最大为 1 MB。")
        else:
            try:
                df = pd.read_csv(uploaded_file, dtype="string", encoding="utf-8-sig", keep_default_na=False)
                start = perf_counter()
                audit = audit_characters(df, CORPUS_DB, dialect=batch_dialect)
                elapsed = (perf_counter() - start) * 1000
                st.session_state["batch_result"] = (audit, batch_dialect)
                valid = audit.loc[audit["match_method"] != "invalid_input"]
                local_event(
                    "search", len(valid), int(valid["match_method"].isin(["exact", "converted"]).sum()),
                    "batch", elapsed_ms=elapsed,
                    exact=int((valid["match_method"] == "exact").sum()),
                    converted=int((valid["match_method"] == "converted").sum()),
                )
            except (ValueError, UnicodeError, pd.errors.ParserError) as err:
                st.error(f"文件格式错误：{err}")

    batch_result = st.session_state.get("batch_result")
    if batch_result is not None:
        audit, stored_dialect = batch_result
        if batch_dialect != stored_dialect:
            st.warning("已切换方言，请重新点击“开始批量核查”，以免误读上次的结果。")
        metrics, unique, review = analyze_batch(audit)
        a, b, c, d = st.columns(4)
        a.metric("有效输入行", metrics["valid_rows"])
        b.metric("匹配行数", metrics["matched_rows"])
        c.metric("转换匹配行数", metrics["converted_rows"])
        d.metric("输入行覆盖率", f"{metrics['row_coverage_pct']:.1f}%" if metrics["row_coverage_pct"] is not None else "N/A")
        st.dataframe(audit, hide_index=True, width="stretch")
        st.download_button("下载批量核查结果 CSV", make_csv(audit), "wu_batch_audit.csv", "text/csv", key="download_batch",
                           on_click=record_export if LOCAL_ANALYTICS_ENABLED else "ignore",
                           args=("batch", metrics["valid_rows"], metrics["matched_rows"]))

        st.markdown("#### 统计口径对比")
        st.caption("输入行覆盖率与归一字形覆盖率的分母不同。归一化仅用于搜索去重，不能保证语义等价。")
        compar = pd.DataFrame({
            "口径": ["输入行", "归一去重字形"],
            "覆盖率（%）": [metrics["row_coverage_pct"], metrics["unique_coverage_pct"]],
        }).dropna()
        if not compar.empty:
            fig_cov = px.bar(compar, x="口径", y="覆盖率（%）", text="覆盖率（%）", range_y=[0, 105])
            fig_cov.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            st.plotly_chart(fig_cov, width="stretch", key="batch_coverage_plot")
        st.caption(f"有效输入 {metrics['valid_rows']} 行，归一去重后 {metrics['unique_keys']} 种字形；无效输入 {metrics['invalid_rows']} 行。")
        with st.expander("查看归一去重明细"):
            st.dataframe(unique, hide_index=True, width="stretch")

        st.markdown("#### 候选读音分布与优先核查清单")
        counts = category_counts(unique)
        fig_review = px.bar(counts, x="核查类别", y="归一字形数", text="归一字形数")
        fig_review.update_yaxes(dtick=1, rangemode="tozero")
        st.plotly_chart(fig_review, width="stretch", key="batch_review_plot")
        st.caption("无参考读音优先找其他合法参考资料；多候选读音建议人工结合上下文判断。候选数多不代表错误。")
        if review.empty:
            st.success("当前批次没有按既定规则需要优先核查的字形。")
        else:
            st.dataframe(review, hide_index=True, width="stretch")
            st.download_button("下载优先核查清单 CSV", make_csv(review), "wu_review_queue.csv", "text/csv", key="download_review", on_click="ignore")

with quality_tab:
    st.subheader("公开参考语料的数据质量与结构")
    st.caption("记录缺失和多候选读音属于参考数据特征，不应直接解释为员工的标注错误。")
    q1, q2, q3 = st.columns(3)
    q1.metric("原始同源词条行", f"{int(meta['raw_rows']):,}")
    q2.metric("标准化后的 IPA 记录", f"{int(meta['readings']):,}")
    q3.metric("空白方言单元格", f"{int(meta['missing_cells']):,}")
    plot_data = coverage.assign(方言=lambda x: x["dialect"].map(DISPLAY_NAMES))
    fig = px.bar(plot_data, x="方言", y="characters", text="characters", title="不同方言的参考样本汉字数", labels={"characters": "汉字数"})
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, width="stretch", key="corpus_dialect_coverage")
    st.caption("这是不同来源方言语料的收录量，不能比较语言丰富程度或人口规模。")
    filled = quality.assign(方言=lambda x: x["dialect"].map(DISPLAY_NAMES), 填充率=lambda x: x["sample_fill_rate"] * 100)
    st.dataframe(filled[["方言", "filled_source_rows", "variants", "填充率"]].rename(columns={
        "filled_source_rows": "有读音的原始行", "variants": "展开后读音记录",
    }), hide_index=True, width="stretch")
    st.markdown("#### 上海话参考字形的候选读音数")
    freq = candidate_freq.copy()
    freq["候选数量"] = freq["distinct_ipa"].apply(lambda x: "3+" if x >= 3 else str(x))
    grouped = freq.groupby("候选数量", as_index=False)["characters"].sum()
    st.plotly_chart(px.bar(grouped, x="候选数量", y="characters", text="characters", labels={"characters": "字形数"}), width="stretch", key="corpus_candidate_chart")
    with st.expander("查看多候选 IPA 的字形示例"):
        st.dataframe(multi, hide_index=True, width="stretch")
    with st.expander("同源词条跨方言 SQL JOIN（辅助研究）"):
        comparison = st.selectbox("对照方言", [d for d in DIALECTS if d != "Wu"], format_func=lambda d: DISPLAY_NAMES[d])
        with closing(connect(CORPUS_DB)) as conn:
            paired = compare(conn, comparison)
        st.caption("仅关联同一 source_row 与汉字，不把不同词源读音任意配对。")
        st.dataframe(paired.head(100), hide_index=True, width="stretch")
    st.download_button("下载语料覆盖汇总 CSV", make_csv(filled), "corpus_dialect_quality.csv", "text/csv", key="download_quality", on_click="ignore")

with events_tab:
    st.subheader("本地开发行为指标")
    if not LOCAL_ANALYTICS_ENABLED:
        st.info("隐私保护：产品事件采集默认关闭。仅在自己电脑上设置 `ENABLE_LOCAL_ANALYTICS=1` 后启动网站，才能采集**开发测试事件**。不要把本地 SQLite 日志提交到 GitHub。")
    else:
        events = load_events(EVENT_DB)
        e = summarize_events(events)
        if e["searches"] == 0:
            st.info("尚未采集开发测试事件。尝试执行检索或批量核查。")
        else:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("测试搜索事件", e["searches"])
            m2.metric("零结果率", f"{e['zero_result_rate']:.1%}")
            m3.metric("测试会话数", e["sessions"])
            m4.metric("测试导出点击", e["exports"])
            st.caption("按本地临时会话标识聚合，不是 DAU、真实人数或真实转化率。")
            daily = daily_events(events)
            daily["零结果率（%）"] = daily["zeros"] / daily["searches"] * 100
            fig_daily = px.bar(daily, x="day", y="零结果率（%）", text="零结果率（%）", range_y=[0, 105], labels={"day": "UTC 日期"})
            fig_daily.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_daily.update_xaxes(type="category")
            st.plotly_chart(fig_daily, width="stretch", key="events_daily")
            valid_events = e["character_events"]
            if not valid_events.empty:
                dfm = valid_events.copy()
                dfm["类别"] = dfm.apply(
                    lambda r: "零结果" if r["result_count"] == 0 else (
                        "完全匹配" if r["result_count"] == r["query_length"] else "部分匹配"), axis=1,
                )
                count_df = dfm["类别"].value_counts().rename_axis("类别").reset_index(name="次数")
                st.plotly_chart(px.bar(count_df, x="类别", y="次数", text="次数"), width="stretch", key="events_result_types")
                latency = pd.to_numeric(dfm["duration_ms"], errors="coerce").dropna()
                if len(latency):
                    l1, l2 = st.columns(2)
                    l1.metric("P50 服务端查询耗时", f"{latency.quantile(.5):.2f} ms")
                    l2.metric("P95 服务端查询耗时", f"{latency.quantile(.95):.2f} ms")
                    if len(latency) >= 2:
                        st.plotly_chart(px.histogram(dfm.dropna(subset=["duration_ms"]), x="duration_ms", nbins=min(12, len(latency)), labels={"duration_ms": "耗时（ms）"}), width="stretch", key="events_latency")
                    if len(latency) < 30:
                        st.warning("测试样本少于 30 条，P95 仅用于验证计算流程，不能作为可靠的线上性能指标。")
            st.caption("所有数据都来自本地开发操作；未记录原始输入内容、IP 或设备指纹。会话 UUID 是假名标识而非彻底匿名。")

st.divider()
st.caption("数据来源：WikiHan — Chang et al. (2022), COLING（CC0）。仅以吴语学堂作为背景参考；未复制其数据库。本项目为独立个人演示工具，与腾讯内部平台无连接。")
