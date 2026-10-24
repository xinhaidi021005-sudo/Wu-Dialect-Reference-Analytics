"""Parameterized SQL and reproducible analytical metrics."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from .etl import DIALECTS


def connect(path: str | Path) -> sqlite3.Connection:
    return sqlite3.connect(str(path), timeout=15)


def read_dataframe(con: sqlite3.Connection, sql: str, params: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(sql, con, params=params)


def query_readings(con: sqlite3.Connection, text: str, dialect: str = "全部", max_rows: int = 500) -> pd.DataFrame:
    """Character/IPA literal substring search. User input is always bound, never interpolated."""
    value = text.strip()
    if not value:
        return pd.DataFrame(columns=["character", "dialect", "ipa", "source_row", "middle_chinese"])
    if len(value) > 60:
        raise ValueError("检索关键词不能超过 60 个字符")
    if dialect != "全部" and dialect not in DIALECTS:
        raise ValueError("不支持该方言分类")
    # Escape SQL LIKE wildcard characters: searching '%' means a literal percent.
    value = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    conditions = ["(r.character LIKE ? ESCAPE '\\' OR r.ipa LIKE ? ESCAPE '\\')"]
    params: list[object] = [f"%{value}%", f"%{value}%"]
    if dialect != "全部":
        conditions.append("r.dialect = ?")
        params.append(dialect)
    params.append(int(max(1, min(max_rows, 1000))))
    return read_dataframe(
        con,
        "SELECT r.character,r.dialect,r.ipa,r.source_row,e.middle_chinese "
        "FROM readings r JOIN entries e ON r.source_row=e.source_row "
        "WHERE " + " AND ".join(conditions) + " "
        "ORDER BY CASE WHEN r.character = ? THEN 0 ELSE 1 END, r.character,r.dialect,r.source_row,r.variant_order "
        "LIMIT ?",
        tuple(params[:-1] + [text.strip(), params[-1]]),
    )


def kpis(con: sqlite3.Connection) -> dict:
    row = con.execute(
        """SELECT
        (SELECT COUNT(DISTINCT character) FROM readings WHERE dialect='Wu'),
        (SELECT COUNT(*) FROM readings WHERE dialect='Wu'),
        (SELECT COUNT(DISTINCT character) FROM readings),
        (SELECT COUNT(*) FROM (
             SELECT character FROM readings WHERE dialect='Wu'
             GROUP BY character HAVING COUNT(DISTINCT ipa)>1)),
        (SELECT COUNT(*) FROM (
             SELECT DISTINCT a.character FROM readings a JOIN readings b
             ON a.source_row=b.source_row WHERE a.dialect='Wu' AND b.dialect='Mandarin'))
        """
    ).fetchone()
    keys = ["wu_characters", "wu_readings", "all_characters", "wu_multiple_characters", "wu_mandarin_shared"]
    return dict(zip(keys, row))


def dialect_coverage(con: sqlite3.Connection) -> pd.DataFrame:
    return read_dataframe(
        con,
        "SELECT dialect,COUNT(DISTINCT character) AS characters,COUNT(*) AS readings "
        "FROM readings GROUP BY dialect ORDER BY characters DESC",
    )


def wu_multiple_readings(con: sqlite3.Connection, limit: int = 20) -> pd.DataFrame:
    return read_dataframe(
        con,
        """SELECT character,COUNT(DISTINCT ipa) AS variants,
        GROUP_CONCAT(DISTINCT ipa) AS examples
        FROM readings WHERE dialect='Wu'
        GROUP BY character HAVING COUNT(DISTINCT ipa)>1
        ORDER BY variants DESC,character LIMIT ?""",
        (limit,),
    )


def compare(con: sqlite3.Connection, other_dialect: str = "Mandarin") -> pd.DataFrame:
    if other_dialect not in DIALECTS or other_dialect == "Wu":
        raise ValueError("请选择吴语以外的有效比较方言")
    return read_dataframe(
        con,
        """WITH wu AS (
            SELECT source_row,character,GROUP_CONCAT(DISTINCT ipa) AS wu_ipa
            FROM readings WHERE dialect='Wu' GROUP BY source_row,character
        ), comparison AS (
            SELECT source_row,character,GROUP_CONCAT(DISTINCT ipa) AS other_ipa
            FROM readings WHERE dialect=? GROUP BY source_row,character
        )
        SELECT wu.source_row,wu.character,wu.wu_ipa,comparison.other_ipa
        FROM wu INNER JOIN comparison
          ON wu.source_row=comparison.source_row AND wu.character=comparison.character
        ORDER BY wu.source_row""",
        (other_dialect,),
    )


def quality_coverage(con: sqlite3.Connection) -> pd.DataFrame:
    df = read_dataframe(con, """SELECT dialect,COUNT(DISTINCT source_row) AS filled_source_rows,
         COUNT(*) AS variants FROM readings GROUP BY dialect ORDER BY filled_source_rows DESC""")
    total = con.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    df["sample_fill_rate"] = (df["filled_source_rows"] / total).round(4) if total else 0
    return df


def quality_metadata(con: sqlite3.Connection) -> dict:
    return dict(con.execute("SELECT metric,value FROM etl_quality").fetchall())
