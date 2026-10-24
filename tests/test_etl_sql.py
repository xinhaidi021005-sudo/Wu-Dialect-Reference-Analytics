"""Public sample fixtures: no private data and no worker identifiers."""
from pathlib import Path

from src.etl import build_database, extract_tables
from src.analytics import connect, compare, dialect_coverage, kpis, query_readings

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_wikihan.tsv"


def test_extract_preserves_cognate_rows_and_variant_cleanup():
    entries, readings, metrics = extract_tables(SAMPLE)
    assert (entries.character == "車").sum() == 2
    assert ((readings.character == "車") & (readings.dialect == "Wu")).sum() == 2
    assert (readings.ipa == "-").sum() == 0
    assert metrics["missing_cells"] > 0
    assert metrics["deduplicated_variants"] >= 2


def test_database_sql_is_parameterized(tmp_path):
    db = tmp_path / "test.sqlite"
    build_database(SAMPLE, db)
    with connect(db) as con:
        hit = query_readings(con, "車", "Wu")
        assert len(hit) == 2
        assert query_readings(con, "' OR 1=1 --").empty
        assert query_readings(con, "%", "Wu").empty
        assert kpis(con)["wu_characters"] > 0
        assert not compare(con, "Mandarin").empty
        assert len(dialect_coverage(con)) == 8
