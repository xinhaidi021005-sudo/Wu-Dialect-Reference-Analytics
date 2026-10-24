"""Fetch the full CC0 WikiHan IPA file from its official public repository."""
from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/cmu-llab/wikihan/main/wikihan-ipa.tsv"
ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 WikiHan IPA 语料")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "wikihan-ipa.tsv")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"官方数据源: {SOURCE_URL}")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "WuCorpusAnalyticsStudentProject/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            content = response.read(12_000_001)
    except Exception as exc:
        raise SystemExit(
            f"下载失败: {exc}\n可以在浏览器打开 GitHub 上的 wikihan-ipa.tsv，点击 Raw 下载，"
            f"手动保存到 {args.output}"
        ) from exc
    if len(content) > 12_000_000:
        raise SystemExit("下载文件超过预设大小上限，请手动验证来源")
    if not content.startswith(b"Character\t") or b"\tWu\t" not in content[:150]:
        raise SystemExit("文件头校验失败：不是预期的 WikiHan TSV 文件")
    args.output.write_bytes(content)
    print(f"已保存: {args.output} ({len(content):,} bytes)")
    print("运行 streamlit run app.py 即可载入全量数据；无需爬取 wugniu.com。")


if __name__ == "__main__":
    main()
