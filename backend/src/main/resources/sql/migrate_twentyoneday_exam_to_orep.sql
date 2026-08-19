-- Migrate exam question bank and papers from twentyoneday into OREP.
-- Safe to run repeatedly: imported source rows are tracked in exam_migration_map.

CREATE TABLE IF NOT EXISTS orep.exam_migration_map (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_db VARCHAR(64) NOT NULL,
    source_table VARCHAR(64) NOT NULL,
    source_id BIGINT NOT NULL,
    target_table VARCHAR(64) NOT NULL,
    target_id BIGINT NOT NULL,
    migrated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_exam_migration_source (source_db, source_table, source_id, target_table)
);

DROP PROCEDURE IF EXISTS orep.migrate_twentyoneday_exam_data;

DELIMITER //

CREATE PROCEDURE orep.migrate_twentyoneday_exam_data()
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE v_source_question_id BIGINT;
    DECLARE v_question_type VARCHAR(32);
    DECLARE v_stem TEXT;
    DECLARE v_options_json TEXT;
    DECLARE v_answer_json TEXT;
    DECLARE v_analysis TEXT;
    DECLARE v_category VARCHAR(100);
    DECLARE v_difficulty VARCHAR(32);
    DECLARE v_score INT;
    DECLARE v_status VARCHAR(32);
    DECLARE v_created_at DATETIME;
    DECLARE v_updated_at DATETIME;
    DECLARE v_target_question_id BIGINT;

    DECLARE v_source_paper_id BIGINT;
    DECLARE v_title VARCHAR(255);
    DECLARE v_description TEXT;
    DECLARE v_duration_minutes INT;
    DECLARE v_pass_score INT;
    DECLARE v_paper_status VARCHAR(32);
    DECLARE v_target_paper_id BIGINT;

    DECLARE question_cursor CURSOR FOR
        SELECT
            q.id,
            CASE q.type
                WHEN 'single' THEN 'single'
                WHEN 'multiple' THEN 'multiple'
                WHEN 'judge' THEN 'judge'
                WHEN 'fill' THEN 'blank'
                WHEN 'code' THEN 'programming'
                ELSE 'single'
            END AS question_type,
            q.content AS stem,
            CASE
                WHEN q.type IN ('single', 'multiple') AND q.options IS NOT NULL AND JSON_VALID(q.options) = 1 THEN (
                    SELECT JSON_ARRAYAGG(JSON_OBJECT('key', option_item.option_key, 'text', option_item.option_text))
                    FROM (
                        SELECT
                            jt.option_key,
                            JSON_UNQUOTE(JSON_EXTRACT(q.options, CONCAT('$.', jt.option_key))) AS option_text,
                            jt.option_order
                        FROM JSON_TABLE(
                            JSON_KEYS(q.options),
                            '$[*]' COLUMNS(
                                option_order FOR ORDINALITY,
                                option_key VARCHAR(32) PATH '$'
                            )
                        ) jt
                        ORDER BY jt.option_order
                    ) option_item
                )
                WHEN q.type = 'judge' THEN JSON_ARRAY(
                    JSON_OBJECT('key', 'true', 'text', '正确'),
                    JSON_OBJECT('key', 'false', 'text', '错误')
                )
                ELSE JSON_ARRAY()
            END AS options_json,
            CASE
                WHEN q.type = 'multiple' THEN CAST(CONCAT(
                    '["',
                    REPLACE(REPLACE(REPLACE(TRIM(COALESCE(q.answer, '')), '\\', '\\\\'), '"', '\\"'), ',', '","'),
                    '"]'
                ) AS JSON)
                WHEN q.type = 'judge' AND q.answer = '正确' THEN JSON_ARRAY('true')
                WHEN q.type = 'judge' AND q.answer = '错误' THEN JSON_ARRAY('false')
                ELSE JSON_ARRAY(COALESCE(q.answer, ''))
            END AS answer_json,
            CASE
                WHEN q.type = 'code' THEN CONCAT(
                    COALESCE(q.analysis, ''),
                    IF(q.test_input IS NULL AND q.test_output IS NULL, '', '\n\n原题测试参考：'),
                    IF(q.test_input IS NULL, '', CONCAT('\n输入：', q.test_input)),
                    IF(q.test_output IS NULL, '', CONCAT('\n输出：', q.test_output))
                )
                ELSE q.analysis
            END AS analysis,
            COALESCE(NULLIF(q.first_Category, ''), 'twentyoneday') AS category,
            CASE
                WHEN q.difficulty <= 1 THEN 'easy'
                WHEN q.difficulty = 2 THEN 'normal'
                ELSE 'hard'
            END AS difficulty,
            COALESCE(q.score, 5) AS score,
            CASE WHEN q.is_public = 0 THEN 'disabled' ELSE 'enabled' END AS status,
            q.created_at,
            q.updated_at
        FROM twentyoneday.question q
        WHERE NOT EXISTS (
            SELECT 1
            FROM orep.exam_migration_map m
            WHERE m.source_db = 'twentyoneday'
              AND m.source_table = 'question'
              AND m.source_id = q.id
              AND m.target_table = 'exam_question'
        )
        ORDER BY q.id;

    DECLARE paper_cursor CURSOR FOR
        SELECT
            e.id,
            e.name,
            CONCAT(
                IF(e.type IS NULL OR e.type = '', '', CONCAT('类型：', e.type, '\n')),
                IF(e.scope IS NULL OR e.scope = '', '', CONCAT('范围：', e.scope))
            ) AS description,
            COALESCE(e.duration, 45),
            COALESCE(e.pass_score, 60),
            CASE WHEN e.status = 'draft' THEN 'draft' ELSE 'published' END AS status,
            e.created_at,
            e.updated_at
        FROM twentyoneday.exam e
        WHERE NOT EXISTS (
            SELECT 1
            FROM orep.exam_migration_map m
            WHERE m.source_db = 'twentyoneday'
              AND m.source_table = 'exam'
              AND m.source_id = e.id
              AND m.target_table = 'exam_paper'
        )
        ORDER BY e.id;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN question_cursor;
    question_loop: LOOP
        FETCH question_cursor INTO
            v_source_question_id,
            v_question_type,
            v_stem,
            v_options_json,
            v_answer_json,
            v_analysis,
            v_category,
            v_difficulty,
            v_score,
            v_status,
            v_created_at,
            v_updated_at;
        IF done = 1 THEN
            LEAVE question_loop;
        END IF;

        INSERT INTO orep.exam_question (
            question_type,
            stem,
            options_json,
            answer_json,
            analysis,
            category,
            difficulty,
            score,
            status,
            created_at,
            updated_at
        ) VALUES (
            v_question_type,
            v_stem,
            COALESCE(v_options_json, JSON_ARRAY()),
            COALESCE(v_answer_json, JSON_ARRAY()),
            v_analysis,
            v_category,
            v_difficulty,
            v_score,
            v_status,
            COALESCE(v_created_at, NOW()),
            COALESCE(v_updated_at, NOW())
        );

        SET v_target_question_id = LAST_INSERT_ID();

        INSERT INTO orep.exam_migration_map (source_db, source_table, source_id, target_table, target_id)
        VALUES ('twentyoneday', 'question', v_source_question_id, 'exam_question', v_target_question_id);
    END LOOP;
    CLOSE question_cursor;

    SET done = 0;

    OPEN paper_cursor;
    paper_loop: LOOP
        FETCH paper_cursor INTO
            v_source_paper_id,
            v_title,
            v_description,
            v_duration_minutes,
            v_pass_score,
            v_paper_status,
            v_created_at,
            v_updated_at;
        IF done = 1 THEN
            LEAVE paper_loop;
        END IF;

        INSERT INTO orep.exam_paper (
            title,
            description,
            duration_minutes,
            pass_score,
            status,
            shuffle_questions,
            shuffle_options,
            anti_cheat_enabled,
            created_at,
            updated_at
        ) VALUES (
            v_title,
            v_description,
            GREATEST(1, v_duration_minutes),
            v_pass_score,
            v_paper_status,
            1,
            1,
            1,
            COALESCE(v_created_at, NOW()),
            COALESCE(v_updated_at, NOW())
        );

        SET v_target_paper_id = LAST_INSERT_ID();

        INSERT INTO orep.exam_migration_map (source_db, source_table, source_id, target_table, target_id)
        VALUES ('twentyoneday', 'exam', v_source_paper_id, 'exam_paper', v_target_paper_id);
    END LOOP;
    CLOSE paper_cursor;

    INSERT INTO orep.exam_paper_question (paper_id, question_id, score, sort_order)
    SELECT
        paper_map.target_id AS paper_id,
        question_map.target_id AS question_id,
        COALESCE(eq.score, q.score, 5) AS score,
        COALESCE(eq.sort_order, 0) AS sort_order
    FROM twentyoneday.exam_question eq
    JOIN twentyoneday.exam e ON e.id = eq.exam_id
    JOIN twentyoneday.question q ON q.id = eq.question_id
    JOIN orep.exam_migration_map paper_map
        ON paper_map.source_db = 'twentyoneday'
       AND paper_map.source_table = 'exam'
       AND paper_map.source_id = eq.exam_id
       AND paper_map.target_table = 'exam_paper'
    JOIN orep.exam_migration_map question_map
        ON question_map.source_db = 'twentyoneday'
       AND question_map.source_table = 'question'
       AND question_map.source_id = eq.question_id
       AND question_map.target_table = 'exam_question'
    WHERE NOT EXISTS (
        SELECT 1
        FROM orep.exam_paper_question existing
        WHERE existing.paper_id = paper_map.target_id
          AND existing.question_id = question_map.target_id
    );
END//

DELIMITER ;

CALL orep.migrate_twentyoneday_exam_data();

DROP PROCEDURE IF EXISTS orep.migrate_twentyoneday_exam_data;
