-- Public WikiHan corpus: all figures are properties of this reference file.
-- 1) Per-dialect distinct-character reference coverage and IPA record counts.
SELECT dialect, COUNT(DISTINCT character) AS distinct_characters,
       COUNT(*) AS ipa_records
FROM readings GROUP BY dialect ORDER BY distinct_characters DESC;

-- 2) Candidate IPA distribution for Wu (Shanghainese).
WITH candidates AS (
    SELECT character, COUNT(DISTINCT ipa) AS candidate_count
    FROM readings WHERE dialect='Wu' GROUP BY character
)
SELECT candidate_count, COUNT(*) AS characters
FROM candidates GROUP BY candidate_count ORDER BY candidate_count;

-- 3) Cognate-set-aligned comparison, avoiding character-only joins.
WITH wu AS (
    SELECT source_row, character, GROUP_CONCAT(DISTINCT ipa) AS wu_ipa
    FROM readings WHERE dialect='Wu' GROUP BY source_row,character
), mandarin AS (
    SELECT source_row, character, GROUP_CONCAT(DISTINCT ipa) AS mandarin_ipa
    FROM readings WHERE dialect='Mandarin' GROUP BY source_row,character
)
SELECT wu.source_row, wu.character, wu.wu_ipa, mandarin.mandarin_ipa
FROM wu JOIN mandarin ON wu.source_row=mandarin.source_row
 AND wu.character=mandarin.character;

-- 4) Local event metrics use a SEPARATE events.sqlite database, not the corpus DB.
-- SELECT only event_origin='development_test'; never interpret test sessions as DAU.
