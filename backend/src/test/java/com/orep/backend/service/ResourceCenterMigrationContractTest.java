package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;

class ResourceCenterMigrationContractTest {

    @Test
    void migrationAddsTeamScopeAndUpdatedIndexes() throws Exception {
        String sql = Files.readString(Path.of(
                "src/main/resources/db/migration/V109__resource_center_team_scope.sql"
        ));

        assertTrue(sql.contains("ADD COLUMN team_id BIGINT NULL"));
        assertTrue(sql.contains("idx_resource_team_category_updated"));
        assertTrue(sql.contains("uk_resource_category_team_label"));
    }
}
