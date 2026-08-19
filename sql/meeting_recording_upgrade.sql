-- OREP 会议录制升级：服务端单文件音视频录制
-- MySQL 8.0 兼容，可重复执行。

CREATE TABLE IF NOT EXISTS meeting_recording (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    meeting_id BIGINT NOT NULL COMMENT '会议ID',
    user_id BIGINT NOT NULL COMMENT '发起录制用户ID',
    recording_id VARCHAR(64) DEFAULT NULL COMMENT '录制任务ID',
    status ENUM('STARTING','RECORDING','PROCESSING','READY','FAILED') NOT NULL DEFAULT 'STARTING' COMMENT '录制状态',
    file_path VARCHAR(512) DEFAULT NULL COMMENT '主录制视频对象路径，必须包含音频轨',
    mime_type VARCHAR(100) DEFAULT NULL COMMENT '主视频 MIME 类型',
    size_bytes BIGINT DEFAULT NULL COMMENT '主视频大小',
    has_audio TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否包含音频轨',
    has_video TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否包含视频轨',
    error_message TEXT DEFAULT NULL COMMENT '失败原因',
    camera_file VARCHAR(512) DEFAULT NULL COMMENT '兼容旧版：摄像头视频路径',
    screen_file VARCHAR(512) DEFAULT NULL COMMENT '兼容旧版：屏幕视频路径',
    audio_file VARCHAR(512) DEFAULT NULL COMMENT '兼容旧版：音频路径',
    audio_size_bytes BIGINT DEFAULT NULL COMMENT '兼容旧版：音频大小',
    duration_seconds INT DEFAULT NULL COMMENT '录制时长',
    meeting_title VARCHAR(255) DEFAULT NULL COMMENT '会议标题冗余',
    started_at DATETIME DEFAULT NULL COMMENT '开始录制时间',
    ended_at DATETIME DEFAULT NULL COMMENT '结束录制时间',
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    KEY idx_meeting (meeting_id),
    KEY idx_user (user_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会议录制表';

DELIMITER //
CREATE PROCEDURE add_meeting_recording_column_if_missing(
    IN p_column_name VARCHAR(64),
    IN p_column_definition TEXT
)
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'meeting_recording'
          AND COLUMN_NAME = p_column_name
    ) THEN
        SET @ddl = CONCAT('ALTER TABLE meeting_recording ADD COLUMN ', p_column_name, ' ', p_column_definition);
        PREPARE stmt FROM @ddl;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END//
DELIMITER ;

CALL add_meeting_recording_column_if_missing('recording_id', 'VARCHAR(64) DEFAULT NULL COMMENT ''录制任务ID''');
CALL add_meeting_recording_column_if_missing('status', 'ENUM(''STARTING'',''RECORDING'',''PROCESSING'',''READY'',''FAILED'') NOT NULL DEFAULT ''READY'' COMMENT ''录制状态''');
CALL add_meeting_recording_column_if_missing('file_path', 'VARCHAR(512) DEFAULT NULL COMMENT ''主录制视频对象路径，必须包含音频轨''');
CALL add_meeting_recording_column_if_missing('mime_type', 'VARCHAR(100) DEFAULT NULL COMMENT ''主视频 MIME 类型''');
CALL add_meeting_recording_column_if_missing('size_bytes', 'BIGINT DEFAULT NULL COMMENT ''主视频大小''');
CALL add_meeting_recording_column_if_missing('has_audio', 'TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''是否包含音频轨''');
CALL add_meeting_recording_column_if_missing('has_video', 'TINYINT(1) NOT NULL DEFAULT 0 COMMENT ''是否包含视频轨''');
CALL add_meeting_recording_column_if_missing('error_message', 'TEXT DEFAULT NULL COMMENT ''失败原因''');
CALL add_meeting_recording_column_if_missing('started_at', 'DATETIME DEFAULT NULL COMMENT ''开始录制时间''');
CALL add_meeting_recording_column_if_missing('ended_at', 'DATETIME DEFAULT NULL COMMENT ''结束录制时间''');

DROP PROCEDURE add_meeting_recording_column_if_missing;

ALTER TABLE meeting_recording MODIFY audio_file VARCHAR(512) NULL COMMENT '兼容旧版：音频路径';
ALTER TABLE meeting_recording MODIFY audio_size_bytes BIGINT NULL COMMENT '兼容旧版：音频大小';
ALTER TABLE meeting_recording MODIFY duration_seconds INT NULL COMMENT '录制时长';

UPDATE meeting_recording
SET status = 'READY'
WHERE status IS NULL;
