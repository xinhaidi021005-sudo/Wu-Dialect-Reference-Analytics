# Data provenance and scope

- Upstream repository: https://github.com/cmu-llab/wikihan
- Corpus: `wikihan-ipa.tsv`, a dataset derived from Wiktionary.
- Licence: CC0 (see upstream `LICENSE`); the bundled `sample_wikihan.tsv` is a small excerpt from this public dataset.
- Upstream citation: Chang, Kalvin; Cui, Chenxuan; Kim, Youngmin; Mortensen, David R. (2022). *WikiHan: A New Comparative Dataset for Chinese Languages*. COLING 2022.
- WikiHan's **Wu** column is **Shanghainese** reference data. This tool does **not** represent every Wu variety.
- No scraping, replication, or embedding of the `wugniu.com` dictionary was performed. It is only a background/UX reference.
- Raw CC0 corpus is downloaded by the user via `scripts/fetch_wikihan.py`; it is excluded from Git to keep the repo lightweight.
- A `source_row` is a cognate-set row, not necessarily a unique Chinese character. Different rows for the same character must not be indiscriminately merged in source-level comparison.
- Multiple IPA candidates are legitimate possibilities in the reference source, **not automatically errors**.
- This repository contains no audio, transcripts, queries, employee IDs, annotation outcomes, or proprietary material from Tencent or any other employer.
