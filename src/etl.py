"""ETL for the publicly licensed WikiHan IPA table.

One row in WikiHan represents a cognate-set entry. Never deduplicate
solely by character, because heteronymic characters have multiple entries.
"""
from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {"Character", "Wu"}
META_COLUMN = "Middle Chinese (Baxter and Sagart 2014)"
DIALECTS = ["Wu", "Mandarin", "Cantonese", "Hokkien", "Hakka", "Gan", "Jin", "Xiang"]
DISPLAY_NAMES = {
    "Wu": "吴语（上海话）", "Mandarin": "普通话（北京）", "Cantonese": "粤语（广州）",
    "Hokkien": "闽南语（混合来源）", "Hakka": "客家话（四县）", "Gan": "赣语（南昌）",
    "Jin": "晋语（太原）", "Xiang": "湘语（老湘语）",
}


def _clean(value: Any) -> str:
    if pd.isna(value):
        return ""
    return unicodedata.normalize("NFC", str(value).strip())


def extract_tables(source_path: str | Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Extract relational entry/reading tables and ETL quality statistics."""
    raw = pd.read_csv(source_path, sep="\t", dtype=str, keep_default_na=False)
    missing_cols = REQUIRED_COLUMNS - set(raw.columns)
    if missing_cols:
        raise ValueError(f"缺少必需的列: {sorted(missing_cols)}")
    cols = [d for d in DIALECTS if d in raw.columns]
    entries: list[dict] = []
    readings: list[dict] = []
    missing_cells = 0
    repeated_variants = 0
    invalid_characters = 0
    for source_row, row in enumerate(raw.to_dict("records"), start=1):
        character = _clean(row["Character"])
        if not character or character == "-":
            invalid_characters += 1
            continue
        entries.append({
            "source_row": source_row,
            "character": character,
            "middle_chinese": _clean(row.get(META_COLUMN, "")),
        })
        for dialect in cols:
            value = _clean(row.get(dialect, ""))
            if not value or value == "-":
                missing_cells += 1
                continue
            seen: set[str] = set()
            for variant_idx, segment in enumerate(value.split("/"), start=1):
                ipa = _clean(segment)
                if not ipa or ipa == "-":
                    continue
                if ipa in seen:
                    repeated_variants += 1
                    continue
                seen.add(ipa)
                readings.append({
                    "source_row": source_row,
                    "character": character,
                    "dialect": dialect,
                    "ipa": ipa,
                    "variant_order": variant_idx,
                })
    entries_df = pd.DataFrame(entries, columns=["source_row", "character", "middle_chinese"])
    readings_df = pd.DataFrame(readings, columns=["source_row", "character", "dialect", "ipa", "variant_order"])
    report = {
        "raw_rows": len(raw),
        "valid_entries": len(entries_df),
        "unique_characters": int(entries_df["character"].nunique()),
        "readings": len(readings_df),
        "missing_cells": missing_cells,
        "deduplicated_variants": repeated_variants,
        "invalid_characters": invalid_characters,
        "dialects": len(cols),
        "source_name": Path(source_path).name,
    }
    return entries_df, readings_df, report


def build_database(source_path: str | Path, database_path: str | Path) -> dict:
    """Rebuild normalized SQLite database; replace previous DB only after success."""
    source_path = Path(source_path)
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    entries, readings, quality = extract_tables(source_path)
    temp_path = database_path.with_name(database_path.name + ".tmp")
    temp_path.unlink(missing_ok=True)
    try:
        with sqlite3.connect(temp_path) as conn:
            conn.execute("PRAGMA journal_mode = DELETE")
            entries.to_sql("entries", conn, if_exists="replace", index=False)
            readings.to_sql("readings", conn, if_exists="replace", index=False)
            conn.execute("CREATE UNIQUE INDEX idx_entry_source ON entries(source_row)")
            conn.execute("CREATE INDEX idx_readings_dialect_char ON readings(dialect, character)")
            conn.execute("CREATE INDEX idx_readings_source ON readings(source_row, dialect)")
            conn.execute("CREATE TABLE etl_quality (metric TEXT PRIMARY KEY, value TEXT)")
            conn.executemany(
                "INSERT INTO etl_quality (metric,value) VALUES (?, ?)",
                [(k, str(v)) for k, v in quality.items()],
            )
        temp_path.replace(database_path)
    finally:
        temp_path.unlink(missing_ok=True)
    return quality
