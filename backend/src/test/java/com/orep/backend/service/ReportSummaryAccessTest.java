package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ReportSummaryAccessTest {

    @Test
    void studentParticipantIncludesOwnTeam() {
        ReportSummaryAccess.Clause clause = ReportSummaryAccess.session(false, "STUDENT");
        assertTrue(clause.sql().contains("project_team_member"));
        assertTrue(clause.sql().contains("created_by"));
        assertEquals(2, clause.userIdBindings());
    }

    @Test
    void teacherParticipantIncludesCreatedAndMentoredTeam() {
        ReportSummaryAccess.Clause clause = ReportSummaryAccess.session(false, "TEACHER");
        assertTrue(clause.sql().contains("created_by"));
        assertTrue(clause.sql().contains("project_team_member"));
        assertTrue(clause.sql().contains("mentor_id"));
        assertFalse(clause.sql().contains("tenant"));
        assertEquals(3, clause.userIdBindings());
    }

    @Test
    void teamScopeNeverDumpsWholeTenant() {
        ReportSummaryAccess.Clause teacher = ReportSummaryAccess.session(true, "TEACHER");
        ReportSummaryAccess.Clause student = ReportSummaryAccess.session(true, "STUDENT");
        assertTrue(teacher.sql().contains("project_team_member"));
        assertTrue(student.sql().contains("project_team_member"));
        assertFalse(teacher.sql().contains("tenant"));
    }
}
