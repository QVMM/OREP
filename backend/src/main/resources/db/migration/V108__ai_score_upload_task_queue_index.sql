ALTER TABLE ai_scoring_session
  ADD INDEX idx_ai_scoring_session_upload_queue (created_by, source_type, created_at, id);
