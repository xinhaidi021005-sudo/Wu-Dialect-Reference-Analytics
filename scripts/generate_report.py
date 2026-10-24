"""Reproduce SQL/Pandas corpus quality outputs from the local public dataset."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from src.analytics import connect, dialect_coverage, quality_coverage, quality_metadata
from src.config import CORPUS_DB, FULL_DATA, SAMPLE_DATA
from src.etl import build_database


def main():
    src = FULL_DATA if FULL_DATA.exists() else SAMPLE_DATA
    if not CORPUS_DB.exists() or src.stat().st_mtime > CORPUS_DB.stat().st_mtime:
        build_database(src, CORPUS_DB)
    out = ROOT / "reports" / "tables"
    out.mkdir(parents=True, exist_ok=True)
    with closing(connect(CORPUS_DB)) as con:
        cov = dialect_coverage(con)
        quality = quality_coverage(con)
        meta = quality_metadata(con)
        candidate = pd.read_sql_query("""
            SELECT count_distinct_ipa, COUNT(*) AS character_count FROM (
                SELECT character, COUNT(DISTINCT ipa) count_distinct_ipa
                FROM readings WHERE dialect='Wu' GROUP BY character
            ) GROUP BY count_distinct_ipa ORDER BY count_distinct_ipa
        """, con)
    cov.to_csv(out / "dialect_coverage.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(out / "dialect_fill_rate.csv", index=False, encoding="utf-8-sig")
    candidate.to_csv(out / "wu_candidate_distribution.csv", index=False, encoding="utf-8-sig")
    summary = [
        "# Reproducible corpus analysis (local run)",
        "",
        f"Data source: {src.name}",
        f"Raw source rows: {meta['raw_rows']}",
        f"Expanded IPA rows: {meta['readings']}",
        f"Missing dialect cells: {meta['missing_cells']}",
        "",
        "Denominators: dialect fill rate = source rows with a nonempty dialect pronunciation / valid source rows.",
        "Different language subsets have different coverage; do not infer speaker counts.",
        ""
    ]
    (ROOT / "reports" / "CORPUS_ANALYSIS.md").write_text("\n".join(summary), encoding="utf-8")
    print("Saved local reports in:", out)
    print("Metadata:", meta)


if __name__ == "__main__":
    main()
