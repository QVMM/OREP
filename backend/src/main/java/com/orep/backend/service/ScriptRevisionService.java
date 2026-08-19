package com.orep.backend.service;

import com.orep.backend.entity.Script;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

/**
 * 讲稿确认写回前快照。
 */
@Service
public class ScriptRevisionService {

    private final JdbcTemplate jdbc;

    public ScriptRevisionService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public void snapshot(Script script, Long userId, String source) {
        if (script == null || script.getId() == null) {
            throw new IllegalArgumentException("讲稿无效，无法快照");
        }
        int version = script.getContentVersion() == null || script.getContentVersion() < 1
                ? 1
                : script.getContentVersion();
        String content = script.getContent() == null ? "[]" : script.getContent();
        jdbc.update("""
                INSERT INTO script_revision
                  (script_id, content_version, content, roles, source, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, NOW())
                """,
                script.getId(),
                version,
                content,
                script.getRoles(),
                source == null || source.isBlank() ? "apply_script_patch" : source.trim(),
                userId);
    }
}
