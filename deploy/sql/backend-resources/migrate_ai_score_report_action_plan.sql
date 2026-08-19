SET @action_plan_column_exists := (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = DATABASE()
    AND table_name = 'ai_score_report'
    AND column_name = 'action_plan_json'
);

SET @action_plan_ddl := IF(
  @action_plan_column_exists = 0,
  'ALTER TABLE ai_score_report ADD COLUMN action_plan_json LONGTEXT DEFAULT NULL COMMENT ''可执行行动计划 JSON 数组''',
  'SELECT 1'
);

PREPARE action_plan_statement FROM @action_plan_ddl;
EXECUTE action_plan_statement;
DEALLOCATE PREPARE action_plan_statement;
