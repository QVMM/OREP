package com.orep.backend.service;

/**
 * Who can see which report-summary rows.
 * Teachers see sessions they created plus sessions of teams they mentor or join.
 * Students see their own sessions plus their team's scored sessions.
 * Neither list dumps the whole tenant.
 */
public final class ReportSummaryAccess {
    private ReportSummaryAccess() {
    }

    public record Clause(String sql, int userIdBindings) {
    }

    public static Clause session(boolean teamScope, String role) {
        if (teamScope) {
            return new Clause("""
                    s.team_id IS NOT NULL
                    AND (
                        EXISTS (
                            SELECT 1 FROM project_team_member tm
                            WHERE tm.team_id = s.team_id AND tm.user_id = ?
                        )
                        OR EXISTS (
                            SELECT 1 FROM project_team t
                            WHERE t.id = s.team_id AND t.mentor_id = ?
                        )
                    )
                    """, 2);
        }
        if (isStudent(role)) {
            return new Clause("""
                    (
                        s.created_by = ?
                        OR (
                            s.team_id IS NOT NULL
                            AND EXISTS (
                                SELECT 1 FROM project_team_member tm
                                WHERE tm.team_id = s.team_id AND tm.user_id = ?
                            )
                        )
                    )
                    """, 2);
        }
        if (isTeacher(role)) {
            return new Clause("""
                    (
                        s.created_by = ?
                        OR (
                            s.team_id IS NOT NULL
                            AND (
                                EXISTS (
                                    SELECT 1 FROM project_team_member tm
                                    WHERE tm.team_id = s.team_id AND tm.user_id = ?
                                )
                                OR EXISTS (
                                    SELECT 1 FROM project_team t
                                    WHERE t.id = s.team_id AND t.mentor_id = ?
                                )
                            )
                        )
                    )
                    """, 3);
        }
        return new Clause("s.created_by = ?", 1);
    }

    public static Clause legacy(boolean teamScope, String role) {
        if (teamScope) {
            return new Clause("""
                    b.team_id IS NOT NULL
                    AND (
                        EXISTS (
                            SELECT 1 FROM project_team_member tm
                            WHERE tm.team_id = b.team_id AND tm.user_id = ?
                        )
                        OR EXISTS (
                            SELECT 1 FROM project_team t
                            WHERE t.id = b.team_id AND t.mentor_id = ?
                        )
                    )
                    """, 2);
        }
        if (isStudent(role)) {
            return new Clause("""
                    (
                        m.creator_id = ?
                        OR EXISTS (SELECT 1 FROM meeting_participant mp WHERE mp.meeting_id = m.id AND mp.user_id = ?)
                        OR EXISTS (
                            SELECT 1 FROM project_team_member tm
                            JOIN project_roadshow_binding b2 ON b2.team_id = tm.team_id
                            WHERE tm.user_id = ? AND b2.meeting_id = m.id
                        )
                    )
                    """, 3);
        }
        return new Clause(
                "(m.creator_id = ? OR EXISTS (SELECT 1 FROM meeting_participant mp WHERE mp.meeting_id = m.id AND mp.user_id = ?))",
                2
        );
    }

    static boolean isStudent(String role) {
        return role != null && "STUDENT".equalsIgnoreCase(role.trim());
    }

    static boolean isTeacher(String role) {
        return role != null && "TEACHER".equalsIgnoreCase(role.trim());
    }
}
