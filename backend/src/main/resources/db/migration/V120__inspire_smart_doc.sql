CREATE TABLE IF NOT EXISTS inspire_smart_doc (
    document_id BIGINT PRIMARY KEY,
    content_json MEDIUMTEXT NOT NULL,
    schema_version INT NOT NULL DEFAULT 1,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_inspire_smart_doc_document
        FOREIGN KEY (document_id) REFERENCES inspire_office_document(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
