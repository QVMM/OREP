ALTER TABLE ai_jury_session
  ADD COLUMN scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID';

ALTER TABLE ai_jury_session
  MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空';

CREATE INDEX idx_jury_session_scoring_session_status ON ai_jury_session (scoring_session_id, status);

ALTER TABLE ai_judge_report
  ADD COLUMN scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID';

ALTER TABLE ai_judge_report
  MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空';

CREATE INDEX idx_judge_report_scoring_session ON ai_judge_report (scoring_session_id);

ALTER TABLE ai_jury_aggregate
  ADD COLUMN scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID';

ALTER TABLE ai_jury_aggregate
  MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空';

CREATE INDEX idx_jury_aggregate_scoring_session ON ai_jury_aggregate (scoring_session_id);
