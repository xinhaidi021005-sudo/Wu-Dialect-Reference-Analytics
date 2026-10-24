"""Local, opt-in, pseudonymous DEVELOPMENT events. Never store raw queries.

This is NOT a production privacy/compliance solution. Access to the local
SQLite file must be controlled; session UUIDs are pseudonyms, not anonymity.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

EVENT_TYPES = {"search", "export"}
SEARCH_TYPES = {"character", "batch", "ipa"}


def init_events(path: str | Path) -> None:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(file, timeout=15) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_at_utc TEXT NOT NULL DEFAULT (datetime('now')),
            session_id TEXT NOT NULL,
            event_name TEXT NOT NULL,
            query_length INTEGER NOT NULL,
            result_count INTEGER NOT NULL,
            search_type TEXT,
            exact_match_count INTEGER,
            converted_match_count INTEGER,
            duration_ms REAL,
            event_origin TEXT NOT NULL DEFAULT 'legacy_unknown'
        )""")
        existing = {r[1] for r in con.execute("PRAGMA table_info(events)")}
        for col, decl in {
            "search_type": "TEXT",
            "exact_match_count": "INTEGER",
            "converted_match_count": "INTEGER",
            "duration_ms": "REAL",
            "event_origin": "TEXT NOT NULL DEFAULT 'legacy_unknown'",
        }.items():
            if col not in existing:
                con.execute(f"ALTER TABLE events ADD COLUMN {col} {decl}")
        con.execute("CREATE INDEX IF NOT EXISTS idx_events_date_type ON events(event_at_utc,search_type)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id)")


def log_event(
    path: str | Path,
    session_id: str,
    event_name: str,
    query_length: int,
    result_count: int,
    *,
    search_type: str | None = None,
    exact_match_count: int | None = None,
    converted_match_count: int | None = None,
    duration_ms: float | None = None,
) -> None:
    if event_name not in EVENT_TYPES or (search_type is not None and search_type not in SEARCH_TYPES):
        raise ValueError("Unsupported event or search type")
    if any(x < 0 for x in (query_length, result_count)):
        raise ValueError("Counts must be non-negative")
    if any(x is not None and x < 0 for x in (exact_match_count, converted_match_count, duration_ms)):
        raise ValueError("Metrics must be non-negative")
    if event_name == "search" and search_type in {"character", "batch"}:
        if result_count > query_length:
            raise ValueError("Matched characters/rows cannot exceed input length")
        if exact_match_count is not None and converted_match_count is not None:
            if exact_match_count + converted_match_count != result_count:
                raise ValueError("Match counts must add up to matched results")
    init_events(path)
    with sqlite3.connect(path, timeout=15) as con:
        con.execute("""INSERT INTO events (
          session_id,event_name,query_length,result_count,search_type,
          exact_match_count,converted_match_count,duration_ms,event_origin
        ) VALUES (?,?,?,?,?,?,?,?,?)""", (
            session_id, event_name, query_length, result_count, search_type,
            exact_match_count, converted_match_count, duration_ms, "development_test",
        ))


def load_events(path: str | Path) -> pd.DataFrame:
    """Only local developer events; ignore old records without origin information."""
    init_events(path)
    with sqlite3.connect(path, timeout=15) as con:
        return pd.read_sql_query("""SELECT event_at_utc,session_id,event_name,
          query_length,result_count,search_type,exact_match_count,
          converted_match_count,duration_ms FROM events
          WHERE event_origin='development_test' ORDER BY id""", con)


def summarize_events(events: pd.DataFrame) -> dict:
    searches = events.loc[events["event_name"] == "search"].copy()
    s = len(searches)
    zero = int((searches["result_count"] == 0).sum()) if s else 0
    analyzed = searches.loc[searches["search_type"].isin(["character", "batch"])].copy()
    with_results = searches.loc[searches["result_count"] > 0, "session_id"].nunique()
    exports = events.loc[events["event_name"] == "export"]
    return {
        "searches": s,
        "zero_result_count": zero,
        "zero_result_rate": zero / s if s else None,
        "exports": len(exports),
        "sessions": searches["session_id"].nunique(),
        "result_sessions": with_results,
        "export_sessions": exports["session_id"].nunique(),
        "character_events": analyzed,
    }


def daily_events(events: pd.DataFrame) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=["day", "searches", "zeros"])
    searches = events.loc[events["event_name"] == "search"].copy()
    if searches.empty:
        return pd.DataFrame(columns=["day", "searches", "zeros"])
    searches["day"] = searches["event_at_utc"].str[:10]
    searches["zero"] = (searches["result_count"] == 0).astype(int)
    return searches.groupby("day", as_index=False).agg(searches=("zero", "size"), zeros=("zero", "sum"))
