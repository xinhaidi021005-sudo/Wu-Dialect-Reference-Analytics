import sqlite3

import pytest

from src.events import daily_events, init_events, load_events, log_event, summarize_events


def test_local_development_events(tmp_path):
    db = tmp_path / "events.sqlite"
    log_event(db, "sessionA", "search", 2, 2, search_type="character", exact_match_count=0, converted_match_count=2, duration_ms=24.1)
    log_event(db, "sessionB", "search", 2, 0, search_type="character", exact_match_count=0, converted_match_count=0, duration_ms=10.0)
    data = load_events(db)
    summary = summarize_events(data)
    assert (summary["searches"], summary["zero_result_count"], summary["sessions"]) == (2, 1, 2)
    assert summary["zero_result_rate"] == 0.5
    assert daily_events(data)["searches"].sum() == 2
    assert "query_text" not in data.columns
    with pytest.raises(ValueError):
        log_event(db, "x", "search", 2, 3, search_type="character")


def test_upgrade_legacy_events_without_losing_history(tmp_path):
    db = tmp_path / "old.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, event_at_utc TEXT, session_id TEXT, event_name TEXT, query_length INTEGER, result_count INTEGER)")
        con.execute("INSERT INTO events VALUES (1,'2026-01-01 10:00','old','search',2,1)")
    init_events(db)
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        cols = [r[1] for r in con.execute("PRAGMA table_info(events)")]
        assert "duration_ms" in cols and "event_origin" in cols
    # Old events have unknown provenance and are intentionally excluded from new test KPIs.
    assert load_events(db).empty
