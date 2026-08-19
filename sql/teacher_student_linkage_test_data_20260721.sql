-- 教师端 ↔ 学生端联动测试数据（本地开发）
-- 幂等：可重复执行；数据标题统一带【联动测试】便于识别和清理。
USE orep;

INSERT INTO project_task_assignee (task_id, team_id, user_id, sort_order)
SELECT 31, 2, u.id, u.id
FROM users u
WHERE u.id IN (2,3,4)
  AND NOT EXISTS (
    SELECT 1 FROM project_task_assignee a WHERE a.task_id=31 AND a.user_id=u.id
  );

INSERT INTO project_task_submission
  (task_id, team_id, submitter_id, content, version_no, status, submission_type, sync_to_material, created_at)
SELECT 31, 2, 2,
       '【联动测试】已完成组件结构拆分：页面层、业务层、数据层职责清晰；排障记录包含接口超时、空数据和权限异常。',
       1, 'PENDING_REVIEW', 'TRAINING_EVIDENCE', 1, '2026-07-21 14:22:00'
WHERE NOT EXISTS (SELECT 1 FROM project_task_submission WHERE task_id=31 AND submitter_id=2);

INSERT INTO project_task_submission
  (task_id, team_id, submitter_id, content, version_no, status, submission_type, sync_to_material, created_at)
SELECT 31, 2, 3,
       '【联动测试】后端模块说明与排障清单已提交，重点记录数据库索引、接口返回和异常兜底。',
       1, 'PENDING_REVIEW', 'TRAINING_EVIDENCE', 1, '2026-07-21 14:35:00'
WHERE NOT EXISTS (SELECT 1 FROM project_task_submission WHERE task_id=31 AND submitter_id=3);

INSERT INTO project_task_submission
  (task_id, team_id, submitter_id, content, version_no, status, submission_type, sync_to_material, created_at)
SELECT 31, 2, 4,
       '【联动测试】已补充跨模块联调问题三条，待老师确认排障过程是否完整。',
       1, 'PENDING_REVIEW', 'TRAINING_EVIDENCE', 1, '2026-07-21 15:05:00'
WHERE NOT EXISTS (SELECT 1 FROM project_task_submission WHERE task_id=31 AND submitter_id=4);

INSERT INTO project_submission_asset
  (submission_id, task_id, team_id, asset_kind, file_url, file_name, file_size, file_type, sort_order)
SELECT s.id,31,2,'FILE','/uploads/linkage-test/component-structure.pdf','【联动测试】组件结构说明.pdf',245760,'application/pdf',1
FROM project_task_submission s
WHERE s.task_id=31 AND s.submitter_id=2
  AND NOT EXISTS (SELECT 1 FROM project_submission_asset a WHERE a.submission_id=s.id AND a.file_name='【联动测试】组件结构说明.pdf');

INSERT INTO project_material
  (team_id, material_type, name, description, owner_user_id, source_type, file_url, linked_task_id, review_status)
SELECT 2,'DOCS','【联动测试】主功能组件说明','由今日集训提交同步形成，教师资源中心与学生文件中心共用。',2,'TASK_SYNC',
       '/uploads/linkage-test/component-structure.pdf',31,'PENDING_REVIEW'
WHERE NOT EXISTS (SELECT 1 FROM project_material WHERE team_id=2 AND name='【联动测试】主功能组件说明');

INSERT INTO meeting
  (tenant_id,title,creator_id,meeting_code,meeting_password,jitsi_room_id,status,duration_minutes,start_time,end_time,countdown_end_at,created_at)
SELECT 1,'【联动测试】智慧养老项目彩排',1,'726721','0721','orep-linkage-test-20260721','CREATED',60,
       '2026-07-22 16:00:00',NULL,'2026-07-22 17:00:00','2026-07-21 15:10:00'
WHERE NOT EXISTS (SELECT 1 FROM meeting WHERE meeting_code='726721');

INSERT INTO project_roadshow_binding (team_id, meeting_id, roadshow_type, created_by, created_at)
SELECT 2,m.id,'REHEARSAL',1,NOW() FROM meeting m
WHERE m.meeting_code='726721'
  AND NOT EXISTS (SELECT 1 FROM project_roadshow_binding b WHERE b.team_id=2 AND b.meeting_id=m.id);
