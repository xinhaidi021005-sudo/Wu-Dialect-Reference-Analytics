from pathlib import Path


def test_gitignore_has_private_data_protection():
    root = Path(__file__).resolve().parents[1]
    txt = (root / ".gitignore").read_text(encoding="utf-8")
    for term in (".venv/", "data/processed/", "data/wikihan-ipa.tsv", "*.sqlite", ".env"):
        assert term in txt
    # Local running creates ignored databases; existence is not a test failure.
