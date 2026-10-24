import pandas as pd

from src.metrics import analyze_batch, category_counts


def test_coverage_denominators_and_review_queue():
    # Mirrors 6 public demonstration inputs without storing corporate data.
    df = pd.DataFrame([
        ("车", "車", "converted", 2),
        ("马", "馬", "converted", 2),
        ("車", "車", "exact", 2),
        ("馬", "馬", "exact", 2),
        ("月", "月", "exact", 2),
        ("𪚥", "𪚥", "not_found", 0),
    ], columns=["input_character", "normalized_key", "match_method", "candidate_count"])
    m, unique, review = analyze_batch(df)
    assert m["valid_rows"] == 6
    assert m["matched_rows"] == 5
    assert m["converted_rows"] == 2
    assert m["unique_keys"] == 4
    assert m["duplicate_normalized_rows"] == 2
    assert round(m["row_coverage_pct"], 2) == 83.33
    assert m["unique_coverage_pct"] == 75
    assert category_counts(unique)["归一字形数"].tolist() == [1, 3, 0]
    assert review.iloc[0]["review_category"] == "无参考读音"


def test_invalid_rows_do_not_enter_denominator():
    df = pd.DataFrame([
        ("", "", "invalid_input", 0),
        ("馬", "馬", "exact", 1),
    ], columns=["input_character", "normalized_key", "match_method", "candidate_count"])
    m, _, _ = analyze_batch(df)
    assert m["valid_rows"] == 1
    assert m["invalid_rows"] == 1
    assert m["row_coverage_pct"] == 100
