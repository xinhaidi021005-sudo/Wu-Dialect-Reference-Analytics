"""Single-character reference lookup shared by interactive and batch workflows.

A per-character reference is NOT the pronunciation of an entire word.
"""
from __future__ import annotations

import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd
from opencc import OpenCC

from .etl import DIALECTS

RESULT_COLUMNS = [
    "input_character", "normalized_key", "matched_character", "match_method",
    "reference_ipa", "candidate_count", "review_flag",
]


def clean_character(value: object) -> str:
    """Keep exactly what the user typed, apart from whitespace and NFC."""
    if pd.isna(value):
        return ""
    return unicodedata.normalize("NFC", str(value).strip())


def lookup_one(
    conn: sqlite3.Connection,
    character: str,
    dialect: str = "Wu",
    converter: OpenCC | None = None,
) -> dict:
    """Find distinct IPA values; try the original glyph before s2t fallback."""
    if dialect not in DIALECTS:
        raise ValueError("Unsupported dialect")
    char = clean_character(character)
    empty = {
        "input_character": char, "normalized_key": "", "matched_character": "",
        "match_method": "not_found", "reference_ipa": "", "candidate_count": 0,
        "review_flag": "No reference available",
    }
    if len(char) != 1:
        empty.update(match_method="invalid_input", review_flag="Invalid single-character input")
        return empty

    converter = converter or OpenCC("s2t")
    converted = converter.convert(char)
    # A 1-to-many or phrase conversion must never be forced into a single-character key.
    candidates = list(dict.fromkeys([char] + ([converted] if len(converted) == 1 else [])))
    empty["normalized_key"] = converted if len(converted) == 1 else char

    for candidate in candidates:
        ipa_values = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT ipa FROM readings "
                "WHERE dialect=? AND character=? AND ipa IS NOT NULL AND ipa != '' "
                "ORDER BY ipa", (dialect, candidate)
            ).fetchall()
        ]
        if not ipa_values:
            continue
        empty.update(
            normalized_key=candidate,
            matched_character=candidate,
            match_method="exact" if candidate == char else "converted",
            reference_ipa=" | ".join(ipa_values),
            candidate_count=len(ipa_values),
            review_flag="Multiple candidates - review" if len(ipa_values) > 1 else "Reference available",
        )
        break
    return empty


def audit_characters(
    input_df: pd.DataFrame,
    db_path: str | Path,
    dialect: str = "Wu",
    max_rows: int = 500,
) -> pd.DataFrame:
    """Audit a column named `character`; never persist the uploaded content."""
    if "character" not in input_df.columns:
        raise ValueError("CSV must contain a column named character")
    if not 1 <= len(input_df) <= max_rows:
        raise ValueError(f"Please provide 1 to {max_rows} rows")
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"Corpus database missing: {path}")
    converter = OpenCC("s2t")
    cache: dict[str, dict] = {}
    results: list[dict] = []
    with sqlite3.connect(path, timeout=15) as conn:
        for value in input_df["character"]:
            char = clean_character(value)
            if char not in cache:
                cache[char] = lookup_one(conn, char, dialect=dialect, converter=converter)
            # A copy prevents data from one input row affecting another.
            results.append(dict(cache[char]))
    return pd.DataFrame(results, columns=RESULT_COLUMNS)
