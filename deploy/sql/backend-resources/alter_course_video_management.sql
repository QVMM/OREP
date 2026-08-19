-- ============================================================
-- OREP 课程管理与视频播放字段升级
-- ============================================================

ALTER TABLE course_lesson
    ADD COLUMN video_file_path VARCHAR(512) DEFAULT NULL COMMENT '课程视频本地相对路径' AFTER resource_url,
    ADD COLUMN video_mime_type VARCHAR(100) DEFAULT NULL COMMENT '课程视频 MIME 类型' AFTER video_file_path,
    ADD COLUMN video_size_bytes BIGINT DEFAULT NULL COMMENT '课程视频大小' AFTER video_mime_type;

UPDATE course_lesson
SET resource_url = CONCAT('/api/courses/lessons/', id, '/stream')
WHERE video_file_path IS NOT NULL AND video_file_path <> '';
