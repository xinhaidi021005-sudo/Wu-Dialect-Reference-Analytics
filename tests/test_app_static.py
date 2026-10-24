"""Protect against the duplicate-widget bugs found during prototyping."""
import ast
from pathlib import Path


def test_chart_and_button_keys_are_explicit_and_unique():
    tree = ast.parse((Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8"))
    keys = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"plotly_chart", "download_button", "file_uploader"}:
            continue
        kw = {k.arg: k.value for k in node.keywords if k.arg is not None}
        assert "key" in kw, f"Missing key on {node.func.attr} line {node.lineno}"
        assert isinstance(kw["key"], ast.Constant), "Widget keys should be literal strings"
        keys.append(kw["key"].value)
    assert len(keys) == len(set(keys)), "Duplicate Streamlit keys"
    assert len(keys) >= 10
