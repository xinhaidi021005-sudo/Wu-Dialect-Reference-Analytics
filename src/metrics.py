"""Clear denominators for batch reference availability and review triage."""
from __future__ import annotations

import pandas as pd

MATCHED = {"exact", "converted"}
CATEGORIES = ["无参考读音", "多候选读音", "单候选读音"]


def analyze_batch(audit: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Return row/normalized-key metrics, unique-key table and review queue.

    Unicode/OpenCC normalized keys are search aids, NOT linguistic synonymy.
    """
    valid = audit.loc[audit["match_method"] != "invalid_input"].copy()
    valid["matched_flag"] = valid["match_method"].isin(MATCHED)
    n_rows = len(valid)
    n_matched = int(valid["matched_flag"].sum())
    n_converted = int((valid["match_method"] == "converted").sum())
    if n_rows:
        unique = (
            valid.groupby("normalized_key", sort=True, as_index=False)
            .agg(
                input_rows=("input_character", "size"),
                matched_rows=("matched_flag", "sum"),
                input_variants=("input_character", lambda s: " / ".join(dict.fromkeys(s))),
                candidate_count=("candidate_count", "max"),
            )
        )
        unique["has_reference"] = unique["matched_rows"] > 0
        unique["review_category"] = unique.apply(
            lambda r: "无参考读音" if not r["has_reference"]
            else "多候选读音" if r["candidate_count"] > 1
            else "单候选读音", axis=1
        )
    else:
        unique = pd.DataFrame(columns=[
            "normalized_key", "input_rows", "matched_rows", "input_variants",
            "candidate_count", "has_reference", "review_category",
        ])
    n_unique = len(unique)
    n_unique_matched = int(unique["has_reference"].sum()) if n_unique else 0
    metrics = {
        "input_rows": len(audit),
        "valid_rows": n_rows,
        "invalid_rows": len(audit) - n_rows,
        "matched_rows": n_matched,
        "converted_rows": n_converted,
        "row_coverage_pct": 100 * n_matched / n_rows if n_rows else None,
        "unique_keys": n_unique,
        "matched_unique_keys": n_unique_matched,
        "unique_coverage_pct": 100 * n_unique_matched / n_unique if n_unique else None,
        "duplicate_normalized_rows": n_rows - n_unique,
    }
    review = unique.loc[unique["review_category"] != "单候选读音"].copy()
    if not review.empty:
        review["priority"] = review["review_category"].map({"无参考读音": 1, "多候选读音": 2})
        review = review.sort_values(["priority", "normalized_key"]).drop(columns="priority")
    return metrics, unique, review


def category_counts(unique: pd.DataFrame) -> pd.DataFrame:
    return (
        unique["review_category"].value_counts()
        .reindex(CATEGORIES, fill_value=0)
        .rename_axis("核查类别").reset_index(name="归一字形数")
    )
