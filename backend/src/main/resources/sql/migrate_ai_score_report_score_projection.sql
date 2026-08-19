SET @score_projection_column_exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = DATABASE()
    AND table_name = 'ai_score_report'
    AND column_name = 'score_projection_json'
);

SET @score_projection_ddl := IF(
  @score_projection_column_exists = 0,
  'ALTER TABLE ai_score_report ADD COLUMN score_projection_json LONGTEXT DEFAULT NULL COMMENT ''全部整改验收后的规则情景预测 JSON''',
  'SELECT 1'
);

PREPARE score_projection_statement FROM @score_projection_ddl;
EXECUTE score_projection_statement;
DEALLOCATE PREPARE score_projection_statement;
