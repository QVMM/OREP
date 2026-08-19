-- Cloud hotfix 2026-08-18
-- Symptom: teacher report list SQLException 1267
--   Illegal mix of collations (utf8mb4_0900_ai_ci, IMPLICIT)
--   and (utf8mb4_unicode_ci, IMPLICIT) for operation '='
-- Cause: ai_score_docket / ai_score_docket_run were created without COLLATE,
--   so MySQL 8 used utf8mb4_0900_ai_ci. ai_scoring_session.docket_id is
--   utf8mb4_unicode_ci. JOIN d.docket_id = s.docket_id then fails.
--   Same query backs student / teacher historical report lists.
-- Safe to re-run. Does not change application code or scores.

SELECT TABLE_NAME, TABLE_COLLATION
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('ai_scoring_session', 'ai_score_report', 'ai_score_docket', 'ai_score_docket_run');

SELECT TABLE_NAME, COLUMN_NAME, CHARACTER_SET_NAME, COLLATION_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND COLUMN_NAME = 'docket_id';

ALTER TABLE ai_score_docket
  CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE ai_score_docket_run
  CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT TABLE_NAME, TABLE_COLLATION
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME IN ('ai_score_docket', 'ai_score_docket_run');
