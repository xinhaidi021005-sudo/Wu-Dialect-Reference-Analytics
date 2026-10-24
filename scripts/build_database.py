"""CLI: python scripts/build_database.py [--sample]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.config import CORPUS_DB, FULL_DATA, SAMPLE_DATA
from src.etl import build_database


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="Force bundled CC0 mini sample")
    args = ap.parse_args()
    src = SAMPLE_DATA if args.sample or not FULL_DATA.exists() else FULL_DATA
    metrics = build_database(src, CORPUS_DB)
    print("Source:", src)
    print("Database:", CORPUS_DB)
    print("Rows:", metrics["raw_rows"])
    print("Normalized IPA records:", metrics["readings"])
    print("Build completed.")


if __name__ == "__main__":
    main()
