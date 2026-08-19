#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为云端「内测1队」(第一阶段内测团队) 注入正向展示用真实数据。

原则：
- 写入 MySQL 真实表，首页 / 训练计划 / AI 评分等接口原样读取
- 可重复执行：幂等清理带 seed 标记的样例数据后再写入
- 仅作用于 team_id=6 / camp_id=5 / 学生 user 26-29

用法（在部署机或本机经 docker exec mysql）：
  python3 scripts/seed_neice1_promo_data.py --host ... --user root --password ... --database orep
  或：通过 stdin 生成 SQL 后 mysql 执行：
  python3 scripts/seed_neice1_promo_data.py --sql-only > /tmp/seed.sql
"""

from __future__ import annotations

import argparse
import json
import textwrap
import uuid
from datetime import date, datetime, timedelta

TEAM_ID = 6
CAMP_ID = 5
TENANT_ID = 1
TEACHER_ID = 25
STUDENT_IDS = [26, 27, 28, 29]
SEED_TAG = "neice1_promo_seed_v2"
SEED_TAG_PREFIX = "neice1_promo_seed"  # 清理时匹配历史版本
MEETING_TITLE = "【宣传样例】内测1队·备赛路演复盘"
SESSION_NO_PREFIX = "SC-NEICE1-PROMO"

# 今日按产品约定 Asia/Shanghai；脚本部署日 2026-08-12
TODAY = date(2026, 8, 12)
# 训练营 day1（camp_id=5）
CAMP_START = date(2026, 7, 31)
# 每日学习时长下限（秒）：≥ 4 小时
MIN_DAILY_SECONDS = 4 * 3600

DAY_TITLES = {
    1: "第 1 天 草莓精准智控-环境搭建",
    2: "第 2 天 传感器数据采集联调",
    3: "第 3 天 病虫害识别与预警",
    4: "第 4 天 智能灌溉控制闭环",
    5: "第 5 天 数据大屏与运营看板",
    6: "第 6 天 路演大纲与故事线",
    7: "第 7 天 逐字稿与 PPT 初版",
    8: "第 8 天 模块联调与现场演示",
    9: "第 9 天 路演彩排（一）",
    10: "第 10 天 问题复盘与优化",
    11: "第 11 天 路演彩排（二）",
    12: "第 12 天 评分整改落地",
    13: "第 13 天 冲刺打磨与终演准备",
    14: "第 14 天 全流程彩排",
    15: "第 15 天 评委视角精修",
    16: "第 16 天 演示稳定性加固",
    17: "第 17 天 团队协同终训",
    18: "第 18 天 正式演练",
    19: "第 19 天 细节打磨",
    20: "第 20 天 赛前复盘",
    21: "第 21 天 赛前静默与状态调整",
}

DAY_SUMMARIES = {
    1: "完成开发环境、代码仓库与项目脚手架搭建，明确分工。",
    2: "完成温湿度/光照传感器采集链路，验证实时入库。",
    3: "完成病虫害识别模型接入与预警阈值策略。",
    4: "完成灌溉控制指令下发与安全互锁。",
    5: "完成运营看板核心指标与可视化。",
    6: "定稿路演故事线与模块讲解顺序。",
    7: "完成逐字稿与 PPT 初版，对齐五维评分观测点。",
    8: "完成端到端演示联调，记录故障与备份方案。",
    9: "首次完整彩排，记录时长与卡点。",
    10: "按彩排问题清单完成技术与表达优化。",
    11: "二次彩排，验证改进效果与衔接。",
    12: "对照 AI 评分报告完成整改项闭环。",
    13: "终演准备：稳定性、表达节奏与应急预案。",
}


def sql_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def sql_json(obj) -> str:
    return sql_str(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def build_dimensions(overall_hint: float = 82.5) -> dict:
    """官方五维正向样例（与首页雷达/报告字段兼容）。"""
    return {
        "skill_level": {
            "name": "技能水平",
            "max_score": 60,
            "score": 49.5,
            "items": [
                {
                    "name": "操作规范性",
                    "max_score": 10,
                    "score": 8.5,
                    "reason": "路演中明确遵循国标与项目开发规范，展示了权限控制与操作日志。",
                    "improvement": "可补充标准编号与合规检查截图，进一步提升可核验性。",
                },
                {
                    "name": "技能熟练度",
                    "max_score": 15,
                    "score": 12.5,
                    "reason": "传感采集、灌溉控制、AI 识别模块演示流畅，故障切换在 30 秒内完成。",
                    "improvement": "正式赛前再做一次全链路压测。",
                },
                {
                    "name": "任务难易度",
                    "max_score": 15,
                    "score": 12.0,
                    "reason": "覆盖物联网采集、边缘识别、自动控制与运营看板，任务链条完整。",
                    "improvement": "可补充高并发/异常工况的处理说明。",
                },
                {
                    "name": "技术先进性",
                    "max_score": 15,
                    "score": 12.0,
                    "reason": "采用轻量化模型与实时通信，技术选型有明确理由。",
                    "improvement": "增加与传统方案的对比指标图。",
                },
                {
                    "name": "现场讲解效果",
                    "max_score": 5,
                    "score": 4.5,
                    "reason": "结构清晰、重点突出，时长控制在 55 分钟左右，节奏稳定。",
                    "improvement": "个别术语可再口语化。",
                },
            ],
        },
        "professionalism": {
            "name": "职业素养",
            "max_score": 10,
            "score": 8.5,
            "items": [
                {
                    "name": "职业道德与行为规范",
                    "max_score": 4,
                    "score": 3.5,
                    "reason": "具备知识产权与数据安全意识，展示脱敏方案。",
                    "improvement": "可补充开源组件 License 清单。",
                },
                {
                    "name": "工匠精神",
                    "max_score": 3,
                    "score": 2.5,
                    "reason": "有明确迭代记录与优化前后对比。",
                    "improvement": "补一张质量门禁流水线截图。",
                },
                {
                    "name": "安全意识",
                    "max_score": 3,
                    "score": 2.5,
                    "reason": "权限分级、日志审计与应急预案齐全。",
                    "improvement": "可附漏洞扫描摘要。",
                },
            ],
        },
        "application_value": {
            "name": "应用价值",
            "max_score": 10,
            "score": 8.5,
            "items": [
                {
                    "name": "实用性",
                    "max_score": 4,
                    "score": 3.5,
                    "reason": "面向大棚种植场景，痛点与方案匹配清晰。",
                    "improvement": "补充试点用户反馈截图。",
                },
                {
                    "name": "经济性",
                    "max_score": 3,
                    "score": 2.5,
                    "reason": "给出硬件与运维成本对比，节约路径清楚。",
                    "improvement": "完善回本周期测算表。",
                },
                {
                    "name": "可持续性",
                    "max_score": 3,
                    "score": 2.5,
                    "reason": "模块化架构，具备扩展与迭代路线。",
                    "improvement": "补充商业化推广里程碑。",
                },
            ],
        },
        "teamwork": {
            "name": "团队合作",
            "max_score": 10,
            "score": 9.0,
            "items": [
                {
                    "name": "团队精神",
                    "max_score": 5,
                    "score": 4.5,
                    "reason": "四人分工明确，讲解与演示交接自然。",
                    "improvement": "可增加共同目标一句话收束。",
                },
                {
                    "name": "沟通协作",
                    "max_score": 5,
                    "score": 4.5,
                    "reason": "故障处理时协作有序，现场互补到位。",
                    "improvement": "增加更多交叉补充。",
                },
            ],
        },
        "innovation": {
            "name": "创新创意",
            "max_score": 10,
            "score": 7.0,
            "items": [
                {
                    "name": "创新意识",
                    "max_score": 4,
                    "score": 3.0,
                    "reason": "识别+控制闭环与轻量化部署结合有亮点。",
                    "improvement": "突出原创算法/协议部分。",
                },
                {
                    "name": "创新成效",
                    "max_score": 6,
                    "score": 4.0,
                    "reason": "给出效率提升与成本下降的量化表述。",
                    "improvement": "补充数据来源与对比图表。",
                },
            ],
        },
    }


def build_priorities() -> list:
    return [
        {
            "priority": 1,
            "dimension": "技能水平",
            "issue": "个别技术对比数据仍偏口头，评委可核验证据不足。",
            "suggestion": "在 PPT 中补充性能 benchmark 与合规检查截图，增强可验证性。",
        },
        {
            "priority": 2,
            "dimension": "应用价值",
            "issue": "试点成效有数据，但缺少真实用户侧证据。",
            "suggestion": "补充基地照片、农户反馈或使用频次统计。",
        },
        {
            "priority": 3,
            "dimension": "创新创意",
            "issue": "创新成效表述较强，来源说明可再扎实。",
            "suggestion": "用对比图标明基线与测量方法，避免空泛百分比。",
        },
    ]


def daily_total_seconds(uid: int, day_no: int) -> int:
    """Deterministic 4.0–6.5h per student/day (always ≥ MIN_DAILY_SECONDS)."""
    # 0..25 → +0.0..+2.5 hours
    bump_tenths = (uid * 7 + day_no * 13) % 26
    return MIN_DAILY_SECONDS + bump_tenths * 360


def split_day_seconds(total: int, uid: int, day_no: int) -> list[tuple[str, str, str, int]]:
    """
    Split one day into 4 activity slots.
    Returns list of (activity_type, source_type, start_hhmmss, seconds).
    source_id is assigned separately (synthetic unique).
    """
    # ratios vary slightly per student so charts look organic
    r0 = 0.38 + ((uid + day_no) % 5) * 0.01
    r1 = 0.22
    r2 = 0.25 - ((uid + day_no) % 4) * 0.01
    r3 = 1.0 - r0 - r1 - r2
    parts = [int(total * r0), int(total * r1), int(total * r2)]
    parts.append(total - sum(parts))
    # evening activity rotates for variety
    evening = ("ROADSHOW", "ROADSHOW_PRACTICE") if day_no % 3 == 0 else (
        ("COLLABORATION", "COLLABORATION") if day_no % 3 == 1 else ("TYPING", "TYPING_PRACTICE")
    )
    slots = [
        ("TRAINING", "TRAINING_DAY_SEED", "08:40:00", parts[0]),
        ("COURSE", "COURSE_LESSON_SEED", "10:30:00", parts[1]),
        ("TASK_BOOK", "TASK_BOOK_SEED", "14:00:00", parts[2]),
        (evening[0], evening[1], "19:10:00", parts[3]),
    ]
    return [(a, s, t, sec) for a, s, t, sec in slots if sec > 0]


def synth_source_id(uid: int, day_no: int, slot: int) -> int:
    """Avoid colliding with real FK ids; unique under (user_id, source_type, source_id)."""
    return 910_000_000 + uid * 10_000 + day_no * 10 + slot


def build_rich_learning_session_sqls(meta: str) -> list[str]:
    """Camp day1 → TODAY inclusive, every student every day ≥4h."""
    lines: list[str] = []
    day_count = (TODAY - CAMP_START).days + 1
    for day_offset in range(day_count):
        d = CAMP_START + timedelta(days=day_offset)
        day_no = day_offset + 1  # camp day_no 1..N
        for uid in STUDENT_IDS:
            total = daily_total_seconds(uid, day_no)
            assert total >= MIN_DAILY_SECONDS
            for slot, (activity, source_type, hhmmss, sec) in enumerate(
                split_day_seconds(total, uid, day_no)
            ):
                started = datetime.combine(d, datetime.strptime(hhmmss, "%H:%M:%S").time())
                ended = started + timedelta(seconds=sec)
                source_id = synth_source_id(uid, day_no, slot)
                lines.append(
                    "INSERT INTO student_learning_session ("
                    "tenant_id, user_id, team_id, activity_type, source_type, source_id, "
                    "started_at, ended_at, duration_seconds, metadata_json, created_at, updated_at"
                    ") VALUES ("
                    f"1, {uid}, 6, {sql_str(activity)}, {sql_str(source_type)}, {source_id}, "
                    f"{sql_str(started.strftime('%Y-%m-%d %H:%M:%S'))}, "
                    f"{sql_str(ended.strftime('%Y-%m-%d %H:%M:%S'))}, "
                    f"{sec}, {meta}, NOW(), NOW()"
                    ");"
                )
    # sanity comment
    lines.append(
        f"-- learning rows: {day_count} days × {len(STUDENT_IDS)} students × ~4 slots "
        f"(≥{MIN_DAILY_SECONDS // 3600}h/day)"
    )
    return lines


def generate_sql() -> str:
    dims = build_dimensions()
    priorities = build_priorities()
    overall = 82.50
    fingerprint = f"fp-{SEED_TAG}-{uuid.uuid4().hex[:16]}"
    session_no = f"{SESSION_NO_PREFIX}-{TODAY.strftime('%Y%m%d')}"
    meeting_code = "618801"  # 6 digits unique enough for seed
    jitsi = f"orep-neice1-promo-{TODAY.strftime('%Y%m%d')}"
    meeting_pwd = "6818"
    meta = sql_json({"seed": SEED_TAG, "purpose": "external_promo_display", "team": "内测1队"})

    lines: list[str] = []
    lines.append("-- seed_neice1_promo_data: real DB rows for 内测1队 promo display")
    lines.append("SET NAMES utf8mb4;")
    lines.append("SET @team_id := 6;")
    lines.append("SET @camp_id := 5;")
    lines.append("SET @tenant_id := 1;")
    lines.append("SET @teacher_id := 25;")
    lines.append("START TRANSACTION;")
    lines.append("")

    # ---------- cleanup previous seed ----------
    lines.append("-- 清理上一轮样例（幂等）")
    lines.append(
        f"DELETE FROM meeting_participant WHERE meeting_id IN "
        f"(SELECT id FROM (SELECT id FROM meeting WHERE title LIKE {sql_str(MEETING_TITLE + '%')}) t);"
    )
    lines.append(
        f"DELETE b FROM project_roadshow_binding b "
        f"JOIN meeting m ON m.id = b.meeting_id WHERE m.title LIKE {sql_str(MEETING_TITLE + '%')};"
    )
    lines.append(
        f"DELETE r FROM ai_score_report r "
        f"JOIN ai_scoring_session s ON s.id = r.session_id "
        f"WHERE s.session_no LIKE {sql_str(SESSION_NO_PREFIX + '%')};"
    )
    lines.append(
        f"DELETE FROM ai_scoring_session WHERE session_no LIKE {sql_str(SESSION_NO_PREFIX + '%')};"
    )
    lines.append(f"DELETE FROM meeting WHERE title LIKE {sql_str(MEETING_TITLE + '%')};")
    lines.append(
        f"DELETE FROM student_learning_session WHERE user_id IN (26,27,28,29) "
        f"AND JSON_UNQUOTE(JSON_EXTRACT(metadata_json, '$.seed')) LIKE {sql_str(SEED_TAG_PREFIX + '%')};"
    )
    lines.append(
        f"DELETE s FROM project_task_submission s "
        f"JOIN project_task t ON t.id = s.task_id "
        f"WHERE t.team_id = 6 AND t.source_type LIKE {sql_str(SEED_TAG_PREFIX + '%')};"
    )
    lines.append(
        f"DELETE dt FROM training_day_task dt "
        f"JOIN project_task t ON t.id = dt.task_id "
        f"WHERE t.team_id = 6 AND t.source_type LIKE {sql_str(SEED_TAG_PREFIX + '%')};"
    )
    lines.append(
        f"DELETE FROM project_task WHERE team_id = 6 AND source_type LIKE {sql_str(SEED_TAG_PREFIX + '%')};"
    )
    lines.append("")

    # ---------- publish & rename training days ----------
    lines.append("-- 发布至今日及过往训练日，并写入正向主题")
    for day_no, title in DAY_TITLES.items():
        summary = DAY_SUMMARIES.get(day_no, "备赛训练日")
        # publish days 1..13 (through TODAY); future stay DRAFT but nicer titles
        if day_no <= 13:
            status = "PUBLISHED"
        else:
            status = "DRAFT"
        lines.append(
            "UPDATE training_day SET "
            f"title = {sql_str(title)}, "
            f"summary = {sql_str(summary)}, "
            f"status = {sql_str(status)}, "
            f"content_html = {sql_str(f'<p>{summary}</p><p>本任务已由内测团队完成关键交付，可用于展示训练节奏与过程管理。</p>')}, "
            "updated_at = NOW() "
            f"WHERE camp_id = 5 AND day_no = {day_no};"
        )
    lines.append("")

    # ---------- tasks + day links for days 2-13 (day1 already has task 55) ----------
    lines.append("-- 为训练日补齐任务（不含已有 day1 task），source_type 打种子标记")
    lines.append(
        textwrap.dedent(
            f"""
            INSERT INTO project_task (
              team_id, stage_key, title, description, owner_user_id, created_by,
              priority, status, due_at, review_required, task_type, task_type_label,
              source_type, created_at, updated_at
            )
            SELECT
              6,
              'TRAINING',
              d.title,
              d.summary,
              26,
              25,
              'MEDIUM',
              CASE WHEN d.training_date < CURDATE() THEN 'DONE' WHEN d.training_date = CURDATE() THEN 'IN_PROGRESS' ELSE 'TODO' END,
              TIMESTAMP(d.training_date, '20:00:00'),
              1,
              'TRAINING_DAY',
              '训练日任务',
              {sql_str(SEED_TAG)},
              NOW(),
              NOW()
            FROM training_day d
            WHERE d.camp_id = 5 AND d.day_no BETWEEN 2 AND 13
              AND NOT EXISTS (
                SELECT 1 FROM training_day_task dt WHERE dt.training_day_id = d.id
              );
            """
        ).strip()
    )
    lines.append("")
    lines.append(
        textwrap.dedent(
            f"""
            INSERT INTO training_day_task (training_day_id, task_id, is_primary, sort_order, created_at)
            SELECT d.id, t.id, 1, 0, NOW()
            FROM training_day d
            JOIN project_task t ON t.team_id = 6 AND t.title = d.title AND t.source_type = {sql_str(SEED_TAG)}
            WHERE d.camp_id = 5 AND d.day_no BETWEEN 2 AND 13
              AND NOT EXISTS (
                SELECT 1 FROM training_day_task dt WHERE dt.training_day_id = d.id AND dt.task_id = t.id
              );
            """
        ).strip()
    )
    # mark original day1 task as DONE for display
    lines.append(
        "UPDATE project_task SET status = 'DONE', updated_at = NOW() WHERE id = 55 AND team_id = 6;"
    )
    lines.append("")

    # ---------- submissions for students: days 1-11 APPROVED, day 12 PENDING ----------
    lines.append("-- 学生提交记录：过去多天 APPROVED，近期 PENDING，制造真实完成进度")
    for uid in STUDENT_IDS:
        # days 1-11 approved
        lines.append(
            textwrap.dedent(
                f"""
                INSERT INTO project_task_submission (
                  task_id, team_id, submitter_id, content, version_no, status,
                  reviewer_id, review_comment, reviewed_at, created_at,
                  submission_type, sync_to_material
                )
                SELECT
                  dt.task_id,
                  6,
                  {uid},
                  CONCAT('【{SEED_TAG}】学生完成训练日提交：', d.title, '。已完成环境/代码/演示材料整理，并同步团队协作文档。'),
                  1,
                  'APPROVED',
                  25,
                  '完成质量良好，继续保持节奏。',
                  TIMESTAMP(d.training_date, '21:10:00'),
                  TIMESTAMP(d.training_date, '18:30:00'),
                  'DOCUMENT',
                  1
                FROM training_day d
                JOIN training_day_task dt ON dt.training_day_id = d.id AND dt.is_primary = 1
                WHERE d.camp_id = 5 AND d.day_no BETWEEN 1 AND 11
                  AND NOT EXISTS (
                    SELECT 1 FROM project_task_submission s
                    WHERE s.task_id = dt.task_id AND s.submitter_id = {uid}
                  );
                """
            ).strip()
        )
        # day 12 pending
        lines.append(
            textwrap.dedent(
                f"""
                INSERT INTO project_task_submission (
                  task_id, team_id, submitter_id, content, version_no, status,
                  created_at, submission_type, sync_to_material
                )
                SELECT
                  dt.task_id, 6, {uid},
                  CONCAT('【{SEED_TAG}】整改项已提交，待指导教师确认。'),
                  1, 'PENDING_REVIEW',
                  TIMESTAMP(d.training_date, '19:00:00'),
                  'DOCUMENT', 1
                FROM training_day d
                JOIN training_day_task dt ON dt.training_day_id = d.id AND dt.is_primary = 1
                WHERE d.camp_id = 5 AND d.day_no = 12
                  AND NOT EXISTS (
                    SELECT 1 FROM project_task_submission s
                    WHERE s.task_id = dt.task_id AND s.submitter_id = {uid}
                  );
                """
            ).strip()
        )
    lines.append("")

    # ---------- learning sessions: 训练营 day1 → 今天，每天 ≥4h ----------
    lines.append("-- 学习时长（student_learning_session）：营期至今每天 ≥4 小时，首页近一周柱图饱满")
    lines.extend(build_rich_learning_session_sqls(meta))
    lines.append("")

    # ---------- video learning progress on day1 resource ----------
    lines.append("-- 训练视频学习进度（training_learning_progress）")
    for uid in STUDENT_IDS:
        lines.append(
            textwrap.dedent(
                f"""
                INSERT INTO training_learning_progress (
                  user_id, learning_resource_id, learned_seconds, progress_percent, status,
                  last_learned_at, completed_at, created_at, updated_at,
                  actual_learning_seconds, last_position_seconds, video_duration_seconds
                )
                SELECT {uid}, r.id, 1260, 100, 'COMPLETED',
                       NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 2 DAY, NOW(), NOW(),
                       1260, 1260, 1260
                FROM training_day_learning_resource r
                WHERE r.training_day_id = 85
                ON DUPLICATE KEY UPDATE
                  learned_seconds = GREATEST(learned_seconds, 1260),
                  actual_learning_seconds = GREATEST(actual_learning_seconds, 1260),
                  progress_percent = 100,
                  status = 'COMPLETED',
                  last_learned_at = VALUES(last_learned_at),
                  completed_at = COALESCE(completed_at, VALUES(completed_at)),
                  updated_at = NOW();
                """
            ).strip()
        )
    lines.append("")

    # ---------- meeting + roadshow + participants ----------
    lines.append("-- 路演会议 + 绑定 + 参会（首页 roadshow 统计）")
    lines.append(
        textwrap.dedent(
            f"""
            INSERT INTO meeting (
              tenant_id, title, creator_id, meeting_code, meeting_password, jitsi_room_id,
              status, duration_minutes, start_time, end_time, created_at
            ) VALUES (
              1, {sql_str(MEETING_TITLE)}, 25, {sql_str(meeting_code)}, {sql_str(meeting_pwd)}, {sql_str(jitsi)},
              'ENDED', 58,
              '2026-08-11 15:00:00', '2026-08-11 15:58:00', NOW()
            );
            SET @promo_meeting_id := LAST_INSERT_ID();

            INSERT INTO project_roadshow_binding (team_id, meeting_id, roadshow_type, created_by, created_at)
            VALUES (6, @promo_meeting_id, 'REHEARSAL', 25, NOW());
            """
        ).strip()
    )
    for i, uid in enumerate(STUDENT_IDS):
        joined = f"2026-08-11 14:55:0{i}"
        left = f"2026-08-11 15:58:1{i}"
        dur = 58 * 60 - i * 30
        lines.append(
            "INSERT INTO meeting_participant (meeting_id, user_id, joined_at, left_at, duration_seconds) "
            f"VALUES (@promo_meeting_id, {uid}, {sql_str(joined)}, {sql_str(left)}, {dur});"
        )
    # teacher
    lines.append(
        "INSERT INTO meeting_participant (meeting_id, user_id, joined_at, left_at, duration_seconds) "
        "VALUES (@promo_meeting_id, 25, '2026-08-11 14:50:00', '2026-08-11 16:05:00', 4500);"
    )
    lines.append("")

    # ---------- AI score session + report ----------
    lines.append("-- AI 评分会话 + 报告（首页能力诊断）")
    lines.append(
        textwrap.dedent(
            f"""
            INSERT INTO ai_scoring_session (
              session_no, source_type, source_id, project_id, team_id, meeting_id,
              track_id, track_name, rubric_id, rubric_internal_version, rubric_hash,
              scoring_fingerprint, status, current_stage, progress_percent,
              use_history_memory, jury_enabled, created_by, started_at, completed_at, created_at, updated_at
            ) VALUES (
              {sql_str(session_no)}, 'MEETING', @promo_meeting_id, NULL, 6, @promo_meeting_id,
              'track-it', '新一代信息技术赛道', 'rubric-track-it-v1.2', 'v1.2',
              'fb841b22320c310400d5d2125051fccfa9d1bce257ddff75463ec7cb8a66bc03',
              {sql_str(fingerprint)}, 'completed', 'DONE', 100,
              1, 0, 25, '2026-08-11 16:10:00', '2026-08-11 16:28:00', NOW(), NOW()
            );
            SET @promo_session_id := LAST_INSERT_ID();

            INSERT INTO ai_score_report (
              meeting_id, overall_score, dimensions_json, improvement_priorities_json,
              model, rule_engine_version, status, started_at, completed_at, created_at, updated_at, session_id
            ) VALUES (
              @promo_meeting_id,
              {overall:.2f},
              {sql_json(dims)},
              {sql_json(priorities)},
              'promo-seed',
              'v1.2',
              'completed',
              '2026-08-11 16:10:00',
              '2026-08-11 16:28:00',
              NOW(), NOW(),
              @promo_session_id
            );
            SET @promo_report_id := LAST_INSERT_ID();
            UPDATE ai_scoring_session SET report_id = @promo_report_id WHERE id = @promo_session_id;
            """
        ).strip()
    )
    lines.append("")

    # ---------- second older roadshow for practiceCount > 1 ----------
    lines.append("-- 补充一场较早的路演记录（提升练习次数）")
    lines.append(
        textwrap.dedent(
            f"""
            INSERT INTO meeting (
              tenant_id, title, creator_id, meeting_code, meeting_password, jitsi_room_id,
              status, duration_minutes, start_time, end_time, created_at
            ) VALUES (
              1, {sql_str(MEETING_TITLE + '·初排')}, 25, '618802', '6818',
              {sql_str(jitsi + '-early')},
              'ENDED', 45,
              '2026-08-05 16:00:00', '2026-08-05 16:45:00', NOW()
            );
            SET @promo_meeting_early := LAST_INSERT_ID();
            INSERT INTO project_roadshow_binding (team_id, meeting_id, roadshow_type, created_by, created_at)
            VALUES (6, @promo_meeting_early, 'REHEARSAL', 25, NOW());
            """
        ).strip()
    )
    for uid in STUDENT_IDS:
        lines.append(
            "INSERT INTO meeting_participant (meeting_id, user_id, joined_at, left_at, duration_seconds) "
            f"VALUES (@promo_meeting_early, {uid}, '2026-08-05 15:55:00', '2026-08-05 16:45:00', 2700);"
        )
    lines.append("")

    lines.append("COMMIT;")
    lines.append("")
    lines.append("-- 校验摘要")
    lines.append(
        textwrap.dedent(
            """
            SELECT 'published_days' k, COUNT(*) v FROM training_day WHERE camp_id=5 AND status='PUBLISHED'
            UNION ALL SELECT 'team_tasks', COUNT(*) FROM project_task WHERE team_id=6
            UNION ALL SELECT 'submissions', COUNT(*) FROM project_task_submission s JOIN project_task t ON t.id=s.task_id WHERE t.team_id=6
            UNION ALL SELECT 'learning_sessions', COUNT(*) FROM student_learning_session WHERE user_id IN (26,27,28,29)
            UNION ALL SELECT 'roadshows', COUNT(*) FROM project_roadshow_binding WHERE team_id=6
            UNION ALL SELECT 'score_reports', COUNT(*) FROM ai_score_report r JOIN ai_scoring_session s ON s.id=r.session_id WHERE s.team_id=6 AND r.status='completed'
            UNION ALL SELECT 'latest_score', ROUND(MAX(r.overall_score),2) FROM ai_score_report r JOIN ai_scoring_session s ON s.id=r.session_id WHERE s.team_id=6 AND r.status='completed';
            """
        ).strip()
    )
    return "\n".join(lines) + "\n"


def generate_learning_only_sql() -> str:
    """只刷新学习时长（可单独上线，不影响任务/评分样例）。"""
    meta = sql_json({"seed": SEED_TAG, "purpose": "external_promo_display", "team": "内测1队"})
    lines: list[str] = [
        "-- seed_neice1 learning-only: ≥4h/day from camp start to TODAY",
        "SET NAMES utf8mb4;",
        "START TRANSACTION;",
        f"DELETE FROM student_learning_session WHERE user_id IN ({','.join(str(u) for u in STUDENT_IDS)}) "
        f"AND JSON_UNQUOTE(JSON_EXTRACT(metadata_json, '$.seed')) LIKE {sql_str(SEED_TAG_PREFIX + '%')};",
        "",
    ]
    lines.extend(build_rich_learning_session_sqls(meta))
    lines.append("COMMIT;")
    lines.append("")
    lines.append(
        textwrap.dedent(
            f"""
            SELECT user_id,
                   COUNT(*) AS active_days,
                   ROUND(SUM(day_h), 2) AS total_hours,
                   ROUND(MIN(day_h), 2) AS min_day_hours,
                   ROUND(MAX(day_h), 2) AS max_day_hours
            FROM (
              SELECT user_id, DATE(started_at) d, SUM(duration_seconds)/3600 AS day_h
              FROM student_learning_session
              WHERE user_id IN ({','.join(str(u) for u in STUDENT_IDS)})
                AND JSON_UNQUOTE(JSON_EXTRACT(metadata_json, '$.seed')) LIKE {sql_str(SEED_TAG_PREFIX + '%')}
              GROUP BY user_id, DATE(started_at)
            ) t
            GROUP BY user_id
            ORDER BY user_id;
            """
        ).strip()
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql-only", action="store_true", help="只打印 SQL")
    parser.add_argument("--learning-only", action="store_true", help="只生成/打印学习时长 SQL")
    parser.add_argument("--out", default="", help="写入 SQL 文件路径")
    args = parser.parse_args()
    sql = generate_learning_only_sql() if args.learning_only else generate_sql()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(sql)
        print(f"wrote {args.out} ({len(sql)} bytes)", file=__import__("sys").stderr)
    if args.sql_only or not args.out:
        print(sql)


if __name__ == "__main__":
    main()
