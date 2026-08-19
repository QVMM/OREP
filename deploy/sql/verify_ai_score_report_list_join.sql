SELECT COUNT(*) AS completed_sessions
FROM ai_scoring_session s
JOIN ai_score_report ai ON ai.id = s.report_id AND ai.status = 'completed'
LEFT JOIN meeting m ON m.id = s.meeting_id
LEFT JOIN project_team pt ON pt.id = s.team_id
LEFT JOIN ai_score_docket d ON d.docket_id = s.docket_id
WHERE s.status = 'completed';
