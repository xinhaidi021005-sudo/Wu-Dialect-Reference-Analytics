"""Paths and privacy defaults shared by the app and scripts."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
FULL_DATA = ROOT / "data" / "wikihan-ipa.tsv"
SAMPLE_DATA = ROOT / "data" / "sample_wikihan.tsv"
CORPUS_DB = ROOT / "data" / "processed" / "corpus.sqlite"
EVENT_DB = ROOT / "data" / "processed" / "events.sqlite"

# Explicitly opt in using ENABLE_LOCAL_ANALYTICS=1. Never enable by default on public hosting.
LOCAL_ANALYTICS_ENABLED = os.getenv("ENABLE_LOCAL_ANALYTICS", "0") == "1"
