ALTER TABLE student_certificate
    ADD COLUMN source_type VARCHAR(24) NULL COMMENT 'GENERATED or UPLOADED' AFTER status,
    ADD COLUMN award_level VARCHAR(64) NULL COMMENT '奖项等级' AFTER source_type,
    ADD COLUMN issuer_name VARCHAR(160) NULL COMMENT '颁发单位' AFTER award_level,
    ADD COLUMN original_file_name VARCHAR(255) NULL COMMENT '上传原始文件名' AFTER issuer_name,
    ADD COLUMN mime_type VARCHAR(120) NULL COMMENT '文件 MIME' AFTER original_file_name;

UPDATE student_certificate
SET source_type = 'UPLOADED'
WHERE source_type IS NULL AND pdf_url IS NOT NULL AND pdf_url <> '';

UPDATE student_certificate
SET source_type = 'GENERATED'
WHERE source_type IS NULL;
