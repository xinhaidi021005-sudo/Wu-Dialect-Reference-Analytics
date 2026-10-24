import pandas as pd
import pytest

from src.etl import build_database


def test_batch_lookup_and_opencc(tmp_path):
    pytest.importorskip("opencc")
    from src.lookup import audit_characters

    from pathlib import Path
    sample = Path(__file__).resolve().parents[1] / "data" / "sample_wikihan.tsv"
    db = tmp_path / "corpus.sqlite"
    build_database(sample, db)
    df = audit_characters(pd.DataFrame({"character": ["车", "車", "马", "馬", "月", "𪚥", "车马"]}), db)
    assert df["match_method"].tolist() == ["converted", "exact", "converted", "exact", "exact", "not_found", "invalid_input"]
    assert df.loc[0, "matched_character"] == "車"
    assert df.loc[0, "candidate_count"] == 2
    assert df.loc[5, "candidate_count"] == 0
    assert df.loc[6, "match_method"] == "invalid_input"


def test_batch_rejects_wrong_csv_schema(tmp_path):
    pytest.importorskip("opencc")
    from src.lookup import audit_characters
    with pytest.raises(ValueError, match="character"):
        audit_characters(pd.DataFrame({"wrong_name": ["車"]}), tmp_path / "absent.sqlite")
