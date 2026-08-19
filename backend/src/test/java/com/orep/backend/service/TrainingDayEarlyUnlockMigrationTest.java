package com.orep.backend.service;

import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;

import java.sql.DatabaseMetaData;

import static org.junit.jupiter.api.Assertions.assertEquals;

class TrainingDayEarlyUnlockMigrationTest {

    @Test
    void migrationAddsNullableEarlyUnlockTimestampAndIndex() throws Exception {
        JdbcTemplate jdbc = new JdbcTemplate(new DriverManagerDataSource(
                "jdbc:h2:mem:training_day_early_unlock;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1",
                "sa",
                ""
        ));
        jdbc.execute("DROP ALL OBJECTS");
        jdbc.execute("""
            CREATE TABLE training_day (
              id BIGINT NOT NULL AUTO_INCREMENT,
              status VARCHAR(24) NOT NULL DEFAULT 'PUBLISHED',
              PRIMARY KEY (id)
            )
            """);
        ClassPathResource migration = new ClassPathResource(
                "db/migration/V105__training_day_early_unlock.sql"
        );

        new ResourceDatabasePopulator(migration).execute(jdbc.getDataSource());

        ColumnMetadata column = column(jdbc, "training_day", "early_unlocked_at");
        assertEquals(DatabaseMetaData.columnNullable, column.nullable());
        assertEquals("early_unlocked_at", indexedColumn(
                jdbc,
                "training_day",
                "idx_training_day_early_unlocked_at"
        ));
    }

    private ColumnMetadata column(JdbcTemplate jdbc, String tableName, String columnName) {
        return jdbc.execute((ConnectionCallback<ColumnMetadata>) connection -> {
            try (var columns = connection.getMetaData().getColumns(null, null, tableName, columnName)) {
                if (!columns.next()) throw new AssertionError("missing column " + columnName);
                return new ColumnMetadata(columns.getInt("NULLABLE"));
            }
        });
    }

    private String indexedColumn(JdbcTemplate jdbc, String tableName, String indexName) {
        return jdbc.execute((ConnectionCallback<String>) connection -> {
            try (var indexes = connection.getMetaData().getIndexInfo(null, null, tableName, false, false)) {
                while (indexes.next()) {
                    if (indexName.equalsIgnoreCase(indexes.getString("INDEX_NAME"))) {
                        return indexes.getString("COLUMN_NAME");
                    }
                }
                throw new AssertionError("missing index " + indexName);
            }
        });
    }

    private record ColumnMetadata(int nullable) {}
}
