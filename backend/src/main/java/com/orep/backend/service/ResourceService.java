package com.orep.backend.service;

import com.orep.backend.entity.Resource;
import com.orep.backend.mapper.ResourceMapper;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class ResourceService {

    private final ResourceMapper resourceMapper;
    private final JdbcTemplate jdbc;

    @PostConstruct
    public void ensureMaterialSchema() {
        try {
            jdbc.execute("ALTER TABLE resource ADD COLUMN category VARCHAR(64) DEFAULT 'public'");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE resource ADD COLUMN team_id BIGINT NULL AFTER uploaded_by");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE resource ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("""
                    CREATE TABLE IF NOT EXISTS resource_category (
                      id BIGINT PRIMARY KEY AUTO_INCREMENT,
                      team_id BIGINT NULL,
                      category_key VARCHAR(64) NOT NULL UNIQUE,
                      label VARCHAR(100) NOT NULL,
                      created_by INT NULL,
                      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                      updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    )
                    """);
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE resource_category ADD COLUMN team_id BIGINT NULL AFTER id");
        } catch (Exception ignored) {
        }
        try {
            jdbc.execute("ALTER TABLE resource_category ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP");
        } catch (Exception ignored) {
        }
    }

    public void add(Resource resource) {
        if (resource.getCategory() == null || resource.getCategory().isBlank()) {
            resource.setCategory("public");
        }
        resourceMapper.insert(resource);
    }

    public List<Resource> list() {
        return resourceMapper.findAll();
    }

    public Resource getById(Integer id) {
        return resourceMapper.findById(id);
    }

    public int delete(Integer id) {
        return resourceMapper.deleteById(id);
    }

    public List<Map<String, Object>> listCategories() {
        ensureMaterialSchema();
        return jdbc.queryForList("""
                SELECT id, category_key AS `key`, label, created_at AS createdAt
                FROM resource_category
                WHERE team_id IS NULL
                ORDER BY id ASC
                """);
    }

    public Map<String, Object> createCategory(String label, Integer userId) {
        ensureMaterialSchema();
        String cleanLabel = label == null ? "" : label.trim();
        if (cleanLabel.isEmpty()) {
            throw new IllegalArgumentException("分类名称不能为空");
        }
        if (cleanLabel.length() > 30) {
            cleanLabel = cleanLabel.substring(0, 30);
        }
        String key = "custom_" + Instant.now().toEpochMilli();
        jdbc.update("""
                INSERT INTO resource_category(category_key, label, created_by)
                VALUES (?, ?, ?)
                """, key, cleanLabel, userId);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("key", key.toLowerCase(Locale.ROOT));
        result.put("label", cleanLabel);
        return result;
    }
}
