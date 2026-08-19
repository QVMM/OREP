package com.orep.backend.service;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;

import java.sql.DatabaseMetaData;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.UUID;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AiScoreUploadTaskMigrationTest {

    private JdbcTemplate jdbc;

    @AfterEach
    void cleanUp() {
        if (jdbc != null) {
            jdbc.execute("DROP ALL OBJECTS");
        }
    }

    @Test
    void uploadQueueMigrationCreatesTheOrderedPollingIndexExactlyOnce() throws Exception {
        ClassPathResource migration = new ClassPathResource("db/migration/V108__ai_score_upload_task_queue_index.sql");
        assertTrue(migration.exists(), "V108 migration must exist");
        assertEquals(1, migrationResources().size(), "V108 migration resource must be unique");

        DriverManagerDataSource dataSource = new DriverManagerDataSource();
        dataSource.setDriverClassName("org.h2.Driver");
        dataSource.setUrl("jdbc:h2:mem:upload_queue_migration_" + UUID.randomUUID() + ";MODE=MySQL;DB_CLOSE_DELAY=-1");
        jdbc = new JdbcTemplate(dataSource);
        jdbc.execute("""
                CREATE TABLE ai_scoring_session (
                    id BIGINT PRIMARY KEY,
                    created_by BIGINT,
                    source_type VARCHAR(32),
                    created_at TIMESTAMP
                )
                """);
        new ResourceDatabasePopulator(migration).execute(dataSource);

        List<String> columns = new ArrayList<>();
        try (var connection = dataSource.getConnection(); var indexes = indexInfo(connection.getMetaData())) {
            while (indexes.next()) {
                if ("idx_ai_scoring_session_upload_queue".equalsIgnoreCase(indexes.getString("INDEX_NAME"))) {
                    columns.add(indexes.getString("COLUMN_NAME"));
                }
            }
        }
        assertEquals(List.of("CREATED_BY", "SOURCE_TYPE", "CREATED_AT", "ID"), columns);
    }

    private java.sql.ResultSet indexInfo(DatabaseMetaData metaData) throws Exception {
        return metaData.getIndexInfo(null, null, "AI_SCORING_SESSION", false, false);
    }

    private List<java.net.URL> migrationResources() throws Exception {
        Enumeration<java.net.URL> resources = Thread.currentThread().getContextClassLoader()
                .getResources("db/migration/V108__ai_score_upload_task_queue_index.sql");
        List<java.net.URL> result = new ArrayList<>();
        while (resources.hasMoreElements()) {
            result.add(resources.nextElement());
        }
        return result;
    }
}
