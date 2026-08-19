# OREP Closed-Loop Phase 1 Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可独立运行的统一闭环内核，并把整改草案安全发布为现有项目任务。

**Architecture:** 使用独立 `closed_loop_*` 表保存检查点、评估、追加式裁决、问题、整改批次和轮次关系；通过 `closed_loop_task_link` 关联现有 `project_task`。`ProjectTeamService` 在任务验收时发布领域事件，闭环监听器只推进到待复查，不自动通过检查点。

**Tech Stack:** Java 21、Spring Boot 3.2、JdbcTemplate、MySQL 8、H2、JUnit 5、Mockito、MockMvc。

---

## File map

**Create**

- `backend/src/main/resources/sql/create_closed_loop_tables.sql` — 闭环表结构。
- `deploy/sql/backend-resources/create_closed_loop_tables.sql` — 部署脚本副本。
- `backend/src/main/java/com/orep/backend/config/ClosedLoopProperties.java` — 功能开关。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopSchemaInitializer.java` — 幂等建表。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopTypes.java` — 枚举和状态约束。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopCommands.java` — 内部命令 records。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopRepository.java` — SQL 持久化。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopService.java` — 检查点、评估、裁决。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopRemediationService.java` — 问题、草案和正式任务发布。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopAccessService.java` — tenant/team/角色校验。
- `backend/src/main/java/com/orep/backend/service/closedloop/ProjectTaskAcceptedEvent.java` — 任务验收事件。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopTaskEventListener.java` — 推进待复查。
- `backend/src/main/java/com/orep/backend/controller/ClosedLoopController.java` — 用户端闭环 API。
- `backend/src/main/java/com/orep/backend/dto/closedloop/ClosedLoopRequests.java` — API 请求 DTO。
- `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopSchemaInitializerTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopTypesTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopServiceTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopRemediationServiceTest.java`
- `backend/src/test/java/com/orep/backend/controller/ClosedLoopControllerTest.java`

**Modify**

- `backend/src/main/resources/application.yml` — 增加默认关闭的闭环开关。
- `deploy/docker-compose.yml` — 增加环境变量和 SQL 初始化挂载。
- `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java:1019` — 任务通过后发布事件。
- `backend/src/test/java/com/orep/backend/controller/ProjectTeamControllerTest.java` — 保证既有接口不回归。

## Task 1: Add feature flags

- [ ] **Step 1: Write the failing property binding test**

Create `backend/src/test/java/com/orep/backend/config/ClosedLoopPropertiesTest.java`:

```java
package com.orep.backend.config;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class ClosedLoopPropertiesTest {
    @Test
    void defaultsEveryClosedLoopCapabilityToDisabled() {
        ClosedLoopProperties properties = new ClosedLoopProperties();

        assertThat(properties.isEnabled()).isFalse();
        assertThat(properties.getAdapters().isRoadshow()).isFalse();
        assertThat(properties.getAdapters().isResource()).isFalse();
        assertThat(properties.getAdapters().isExam()).isFalse();
        assertThat(properties.getAdapters().isDailyPlan()).isFalse();
        assertThat(properties.getStageGates().isEnabled()).isFalse();
    }
}
```

- [ ] **Step 2: Run the test and verify it fails**

```bash
cd backend
mvn -Dtest=ClosedLoopPropertiesTest test
```

Expected: compilation failure because `ClosedLoopProperties` does not exist.

- [ ] **Step 3: Implement the property object**

Create `backend/src/main/java/com/orep/backend/config/ClosedLoopProperties.java`:

```java
package com.orep.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "orep.closed-loop")
public class ClosedLoopProperties {
    private boolean enabled;
    private final Adapters adapters = new Adapters();
    private final StageGates stageGates = new StageGates();

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
    public Adapters getAdapters() { return adapters; }
    public StageGates getStageGates() { return stageGates; }

    public static class Adapters {
        private boolean roadshow;
        private boolean resource;
        private boolean exam;
        private boolean dailyPlan;
        public boolean isRoadshow() { return roadshow; }
        public void setRoadshow(boolean roadshow) { this.roadshow = roadshow; }
        public boolean isResource() { return resource; }
        public void setResource(boolean resource) { this.resource = resource; }
        public boolean isExam() { return exam; }
        public void setExam(boolean exam) { this.exam = exam; }
        public boolean isDailyPlan() { return dailyPlan; }
        public void setDailyPlan(boolean dailyPlan) { this.dailyPlan = dailyPlan; }
    }

    public static class StageGates {
        private boolean enabled;
        public boolean isEnabled() { return enabled; }
        public void setEnabled(boolean enabled) { this.enabled = enabled; }
    }
}
```

Append to `backend/src/main/resources/application.yml`:

```yaml
orep:
  closed-loop:
    enabled: ${OREP_CLOSED_LOOP_ENABLED:false}
    adapters:
      roadshow: ${OREP_CLOSED_LOOP_ADAPTERS_ROADSHOW:false}
      resource: ${OREP_CLOSED_LOOP_ADAPTERS_RESOURCE:false}
      exam: ${OREP_CLOSED_LOOP_ADAPTERS_EXAM:false}
      daily-plan: ${OREP_CLOSED_LOOP_ADAPTERS_DAILY_PLAN:false}
    stage-gates:
      enabled: ${OREP_CLOSED_LOOP_STAGE_GATES_ENABLED:false}
```

- [ ] **Step 4: Run the test**

```bash
cd backend
mvn -Dtest=ClosedLoopPropertiesTest test
```

Expected: 1 test passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/java/com/orep/backend/config/ClosedLoopProperties.java backend/src/main/resources/application.yml backend/src/test/java/com/orep/backend/config/ClosedLoopPropertiesTest.java
git commit -m "feat(closed-loop): add guarded rollout properties"
```

## Task 2: Create the core schema

- [ ] **Step 1: Write the failing schema test**

Create `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopSchemaInitializerTest.java`:

```java
package com.orep.backend.service.closedloop;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DriverManagerDataSource;

import static org.assertj.core.api.Assertions.assertThat;

class ClosedLoopSchemaInitializerTest {
    @Test
    void createsAllPhaseOneTablesIdempotently() {
        DriverManagerDataSource dataSource = new DriverManagerDataSource(
                "jdbc:h2:mem:closed-loop;MODE=MySQL;DB_CLOSE_DELAY=-1", "sa", "");
        JdbcTemplate jdbc = new JdbcTemplate(dataSource);
        ClosedLoopSchemaInitializer initializer = new ClosedLoopSchemaInitializer(jdbc);

        initializer.ensureSchema();
        initializer.ensureSchema();

        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME IN (
                  'CLOSED_LOOP_CHECKPOINT',
                  'CLOSED_LOOP_EVALUATION',
                  'CLOSED_LOOP_DECISION',
                  'CLOSED_LOOP_ISSUE',
                  'CLOSED_LOOP_REMEDIATION_BATCH',
                  'CLOSED_LOOP_TASK_DRAFT',
                  'CLOSED_LOOP_TASK_LINK',
                  'CLOSED_LOOP_CYCLE_LINK'
                )
                """, Integer.class);
        assertThat(count).isEqualTo(8);
    }
}
```

- [ ] **Step 2: Run the test and verify it fails**

```bash
cd backend
mvn -Dtest=ClosedLoopSchemaInitializerTest test
```

Expected: compilation failure because the initializer does not exist.

- [ ] **Step 3: Add the SQL schema**

Create identical files at:

- `backend/src/main/resources/sql/create_closed_loop_tables.sql`
- `deploy/sql/backend-resources/create_closed_loop_tables.sql`

```sql
CREATE TABLE IF NOT EXISTS closed_loop_checkpoint (
  id BIGINT NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  project_id BIGINT DEFAULT NULL,
  team_id BIGINT NOT NULL,
  domain_type VARCHAR(32) NOT NULL,
  checkpoint_level VARCHAR(24) NOT NULL,
  subject_type VARCHAR(48) NOT NULL,
  subject_id VARCHAR(120) NOT NULL,
  subject_version VARCHAR(80) NOT NULL,
  cycle_no INT NOT NULL,
  review_mode VARCHAR(40) NOT NULL,
  pass_policy_snapshot LONGTEXT,
  status VARCHAR(40) NOT NULL,
  parent_checkpoint_id BIGINT DEFAULT NULL,
  lock_version INT NOT NULL DEFAULT 0,
  idempotency_key VARCHAR(160) NOT NULL,
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_checkpoint_key (tenant_id, idempotency_key),
  KEY idx_closed_loop_checkpoint_team (tenant_id, team_id, status),
  KEY idx_closed_loop_checkpoint_subject (subject_type, subject_id, subject_version)
);

CREATE TABLE IF NOT EXISTS closed_loop_evaluation (
  id BIGINT NOT NULL AUTO_INCREMENT,
  checkpoint_id BIGINT NOT NULL,
  evaluator_type VARCHAR(32) NOT NULL,
  result VARCHAR(32) NOT NULL,
  score DECIMAL(10,2) DEFAULT NULL,
  confidence DECIMAL(6,4) DEFAULT NULL,
  rule_id VARCHAR(120) DEFAULT NULL,
  rule_version VARCHAR(80) DEFAULT NULL,
  evidence_snapshot LONGTEXT,
  recommendation LONGTEXT,
  status VARCHAR(32) NOT NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_evaluation_key (checkpoint_id, idempotency_key),
  KEY idx_closed_loop_evaluation_checkpoint (checkpoint_id, created_at)
);

CREATE TABLE IF NOT EXISTS closed_loop_decision (
  id BIGINT NOT NULL AUTO_INCREMENT,
  checkpoint_id BIGINT NOT NULL,
  decision_type VARCHAR(32) NOT NULL,
  decision_source VARCHAR(32) NOT NULL,
  decided_by BIGINT DEFAULT NULL,
  reason TEXT,
  based_on_evaluation_id BIGINT DEFAULT NULL,
  supersedes_decision_id BIGINT DEFAULT NULL,
  expected_checkpoint_version INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_closed_loop_decision_checkpoint (checkpoint_id, id)
);

CREATE TABLE IF NOT EXISTS closed_loop_issue (
  id BIGINT NOT NULL AUTO_INCREMENT,
  checkpoint_id BIGINT NOT NULL,
  external_key VARCHAR(160) NOT NULL,
  origin_cycle_no INT NOT NULL,
  category VARCHAR(80) NOT NULL,
  severity VARCHAR(20) NOT NULL,
  title VARCHAR(200) NOT NULL,
  description LONGTEXT,
  source_ref VARCHAR(500) NOT NULL,
  evidence_snapshot LONGTEXT,
  acceptance_criteria LONGTEXT NOT NULL,
  status VARCHAR(32) NOT NULL,
  repeated_failure_count INT NOT NULL DEFAULT 0,
  parent_issue_id BIGINT DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  closed_at DATETIME DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_issue_external (checkpoint_id, external_key),
  KEY idx_closed_loop_issue_status (checkpoint_id, status)
);

CREATE TABLE IF NOT EXISTS closed_loop_remediation_batch (
  id BIGINT NOT NULL AUTO_INCREMENT,
  checkpoint_id BIGINT NOT NULL,
  cycle_no INT NOT NULL,
  status VARCHAR(32) NOT NULL,
  generated_by VARCHAR(32) NOT NULL,
  reviewed_by BIGINT DEFAULT NULL,
  review_comment TEXT,
  published_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_batch_cycle (checkpoint_id, cycle_no)
);

CREATE TABLE IF NOT EXISTS closed_loop_task_draft (
  id BIGINT NOT NULL AUTO_INCREMENT,
  batch_id BIGINT NOT NULL,
  issue_id BIGINT NOT NULL,
  draft_key VARCHAR(160) NOT NULL,
  title VARCHAR(200) NOT NULL,
  description LONGTEXT,
  assignee_scope VARCHAR(24) NOT NULL,
  assignee_user_ids_json TEXT,
  owner_user_id BIGINT DEFAULT NULL,
  priority VARCHAR(20) NOT NULL,
  due_at DATETIME DEFAULT NULL,
  target_ref VARCHAR(500) NOT NULL,
  target_baseline_version VARCHAR(80) DEFAULT NULL,
  acceptance_criteria LONGTEXT NOT NULL,
  recheck_policy VARCHAR(120) NOT NULL,
  status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_draft_key (batch_id, draft_key)
);

CREATE TABLE IF NOT EXISTS closed_loop_task_link (
  id BIGINT NOT NULL AUTO_INCREMENT,
  batch_id BIGINT NOT NULL,
  draft_id BIGINT NOT NULL,
  issue_id BIGINT NOT NULL,
  project_task_id BIGINT NOT NULL,
  checkpoint_id BIGINT NOT NULL,
  cycle_no INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_task_issue (project_task_id, issue_id),
  KEY idx_closed_loop_task_checkpoint (checkpoint_id, cycle_no)
);

CREATE TABLE IF NOT EXISTS closed_loop_cycle_link (
  id BIGINT NOT NULL AUTO_INCREMENT,
  previous_checkpoint_id BIGINT NOT NULL,
  current_checkpoint_id BIGINT NOT NULL,
  trigger_type VARCHAR(40) NOT NULL,
  resolved_issue_ids_json TEXT,
  reopened_issue_ids_json TEXT,
  new_issue_ids_json TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_cycle_pair (previous_checkpoint_id, current_checkpoint_id)
);
```

- [ ] **Step 4: Implement the initializer**

Create `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopSchemaInitializer.java`:

```java
package com.orep.backend.service.closedloop;

import jakarta.annotation.PostConstruct;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;

@Component
public class ClosedLoopSchemaInitializer {
    private final JdbcTemplate jdbc;

    public ClosedLoopSchemaInitializer(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @PostConstruct
    public void ensureSchema() {
        try (InputStream input = new ClassPathResource(
                "sql/create_closed_loop_tables.sql").getInputStream()) {
            String sql = new String(input.readAllBytes(), StandardCharsets.UTF_8);
            for (String statement : sql.split(";")) {
                if (!statement.isBlank()) {
                    jdbc.execute(statement.trim());
                }
            }
        } catch (Exception error) {
            throw new IllegalStateException("统一闭环表初始化失败", error);
        }
    }
}
```

- [ ] **Step 5: Add deployment wiring and run the test**

Add to the MySQL volume list in `deploy/docker-compose.yml`:

```yaml
- ./sql/backend-resources/create_closed_loop_tables.sql:/docker-entrypoint-initdb.d/22-closed-loop.sql:ro
```

Add to backend environment:

```yaml
OREP_CLOSED_LOOP_ENABLED: ${OREP_CLOSED_LOOP_ENABLED:-false}
```

Run:

```bash
cd backend
mvn -Dtest=ClosedLoopSchemaInitializerTest test
```

Expected: 1 test passed.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/resources/sql/create_closed_loop_tables.sql deploy/sql/backend-resources/create_closed_loop_tables.sql deploy/docker-compose.yml backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopSchemaInitializer.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopSchemaInitializerTest.java
git commit -m "feat(closed-loop): add core persistence schema"
```

## Task 3: Define states and transition rules

- [ ] **Step 1: Write failing transition tests**

Create `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopTypesTest.java`:

```java
package com.orep.backend.service.closedloop;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class ClosedLoopTypesTest {
    @Test
    void allowsFailedCheckpointToEnterRemediation() {
        assertThat(ClosedLoopTypes.nextStatus(
                ClosedLoopTypes.CheckpointStatus.FAILED,
                ClosedLoopTypes.Action.START_REMEDIATION
        )).isEqualTo(ClosedLoopTypes.CheckpointStatus.REMEDIATING);
    }

    @Test
    void neverAllowsTaskAcceptanceToPassCheckpointDirectly() {
        assertThatThrownBy(() -> ClosedLoopTypes.nextStatus(
                ClosedLoopTypes.CheckpointStatus.REMEDIATING,
                ClosedLoopTypes.Action.PASS
        )).isInstanceOf(IllegalStateException.class);
    }
}
```

- [ ] **Step 2: Run the test and verify it fails**

```bash
cd backend
mvn -Dtest=ClosedLoopTypesTest test
```

Expected: compilation failure because `ClosedLoopTypes` does not exist.

- [ ] **Step 3: Implement explicit enums and transitions**

Create `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopTypes.java`:

```java
package com.orep.backend.service.closedloop;

import java.util.Map;

public final class ClosedLoopTypes {
    private ClosedLoopTypes() {}

    public enum CheckpointStatus {
        CREATED, ASSESSING, AWAITING_DECISION, PASSED, FAILED,
        REMEDIATING, READY_FOR_RECHECK, ASSESSMENT_FAILED, REOPENED, CANCELLED
    }

    public enum ReviewMode {
        MANUAL_FINAL_REQUIRED, AUTO_PASS_AUDITABLE, ADVISORY_ONLY
    }

    public enum DecisionType { PASSED, FAILED, REWORK_REQUIRED, REVOKED }
    public enum Action {
        START_ASSESSMENT, COMPLETE_ASSESSMENT, FAIL_ASSESSMENT,
        PASS, FAIL, START_REMEDIATION, READY_FOR_RECHECK, REOPEN, CANCEL
    }

    private static final Map<String, CheckpointStatus> TRANSITIONS = Map.ofEntries(
            Map.entry(key(CheckpointStatus.CREATED, Action.START_ASSESSMENT), CheckpointStatus.ASSESSING),
            Map.entry(key(CheckpointStatus.ASSESSING, Action.COMPLETE_ASSESSMENT), CheckpointStatus.AWAITING_DECISION),
            Map.entry(key(CheckpointStatus.ASSESSING, Action.FAIL_ASSESSMENT), CheckpointStatus.ASSESSMENT_FAILED),
            Map.entry(key(CheckpointStatus.AWAITING_DECISION, Action.PASS), CheckpointStatus.PASSED),
            Map.entry(key(CheckpointStatus.AWAITING_DECISION, Action.FAIL), CheckpointStatus.FAILED),
            Map.entry(key(CheckpointStatus.FAILED, Action.START_REMEDIATION), CheckpointStatus.REMEDIATING),
            Map.entry(key(CheckpointStatus.REMEDIATING, Action.READY_FOR_RECHECK), CheckpointStatus.READY_FOR_RECHECK),
            Map.entry(key(CheckpointStatus.PASSED, Action.REOPEN), CheckpointStatus.REOPENED),
            Map.entry(key(CheckpointStatus.REOPENED, Action.START_REMEDIATION), CheckpointStatus.REMEDIATING)
    );

    public static CheckpointStatus nextStatus(CheckpointStatus current, Action action) {
        CheckpointStatus next = TRANSITIONS.get(key(current, action));
        if (next == null) {
            throw new IllegalStateException("unsupported checkpoint transition " + current + " -> " + action);
        }
        return next;
    }

    private static String key(CheckpointStatus status, Action action) {
        return status.name() + ":" + action.name();
    }
}
```

- [ ] **Step 4: Run the test**

```bash
cd backend
mvn -Dtest=ClosedLoopTypesTest test
```

Expected: 2 tests passed.

- [ ] **Step 5: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopTypes.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopTypesTest.java
git commit -m "feat(closed-loop): define auditable state transitions"
```

## Task 4: Implement checkpoint and evaluation persistence

- [ ] **Step 1: Write failing service tests**

Create `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopServiceTest.java` with H2-backed assertions:

```java
@Test
void createCheckpointIsIdempotentAndEvaluationMovesItToAwaitingDecision() {
    long first = service.createCheckpoint(new CreateCheckpoint(
            3L, null, 9L, "ROADSHOW", "ARTIFACT",
            "AI_SCORE_REPORT", "26", "report-30", 1,
            "MANUAL_FINAL_REQUIRED", "roadshow:report:30", 12L
    ));
    long second = service.createCheckpoint(sameCommand());

    assertThat(second).isEqualTo(first);

    service.recordEvaluation(new RecordEvaluation(
            first, "SYSTEM", "FAILED", new BigDecimal("49.5"),
            new BigDecimal("0.97"), "rubric-track-it", "v1.2",
            "{\"anchorIds\":[1,2]}", "需要整改", "report:30:evaluation"
    ));

    assertThat(repository.checkpoint(first).status()).isEqualTo("AWAITING_DECISION");
}
```

The test fixture must create an H2 datasource, run `ClosedLoopSchemaInitializer.ensureSchema()`, and instantiate the repository/service.

- [ ] **Step 2: Run the test and verify it fails**

```bash
cd backend
mvn -Dtest=ClosedLoopServiceTest test
```

Expected: compilation failure because commands, repository and service do not exist.

- [ ] **Step 3: Add typed commands**

Create `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopCommands.java`:

```java
package com.orep.backend.service.closedloop;

import java.math.BigDecimal;

public final class ClosedLoopCommands {
    private ClosedLoopCommands() {}

    public record CreateCheckpoint(
            Long tenantId, Long projectId, Long teamId,
            String domainType, String checkpointLevel,
            String subjectType, String subjectId, String subjectVersion,
            int cycleNo, String reviewMode, String idempotencyKey, Long createdBy
    ) {}

    public record RecordEvaluation(
            Long checkpointId, String evaluatorType, String result,
            BigDecimal score, BigDecimal confidence,
            String ruleId, String ruleVersion,
            String evidenceSnapshot, String recommendation,
            String idempotencyKey
    ) {}
}
```

- [ ] **Step 4: Implement repository and service methods**

Create `ClosedLoopRepository` with:

```java
public Long findCheckpointId(Long tenantId, String key) {
    return jdbc.query("""
            SELECT id FROM closed_loop_checkpoint
            WHERE tenant_id = ? AND idempotency_key = ?
            """, rs -> rs.next() ? rs.getLong(1) : null, tenantId, key);
}

public boolean updateCheckpointStatus(
        long id, String expected, String next, int expectedVersion
) {
    return jdbc.update("""
            UPDATE closed_loop_checkpoint
            SET status = ?, lock_version = lock_version + 1, updated_at = NOW()
            WHERE id = ? AND status = ? AND lock_version = ?
            """, next, id, expected, expectedVersion) == 1;
}
```

Create `ClosedLoopService` with:

```java
@Transactional
public long createCheckpoint(CreateCheckpoint command) {
    Long existing = repository.findCheckpointId(command.tenantId(), command.idempotencyKey());
    if (existing != null) return existing;
    return repository.insertCheckpoint(command);
}

@Transactional
public long recordEvaluation(RecordEvaluation command) {
    CheckpointRow checkpoint = repository.checkpoint(command.checkpointId());
    repository.moveStatus(checkpoint, ASSESSING);
    long evaluationId = repository.upsertEvaluation(command);
    repository.moveStatus(repository.checkpoint(command.checkpointId()), AWAITING_DECISION);
    return evaluationId;
}
```

`upsertEvaluation` must query `(checkpoint_id, idempotency_key)` before insert and return the existing ID on a duplicate request.

- [ ] **Step 5: Run the test**

```bash
cd backend
mvn -Dtest=ClosedLoopServiceTest test
```

Expected: checkpoint idempotency and evaluation transition tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopCommands.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopRepository.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopService.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopServiceTest.java
git commit -m "feat(closed-loop): persist checkpoints and evaluations"
```

## Task 5: Add append-only decisions and reopen behavior

- [ ] **Step 1: Add failing tests**

Append to `ClosedLoopServiceTest`:

```java
@Test
void teacherDecisionRequiresReasonAndRejectsStaleVersion() {
    long checkpointId = assessedCheckpoint();

    assertThatThrownBy(() -> service.recordDecision(new RecordDecision(
            checkpointId, "FAILED", "TEACHER", 12L, "", evaluationId, null, 2
    ))).isInstanceOf(IllegalArgumentException.class);

    service.recordDecision(new RecordDecision(
            checkpointId, "FAILED", "TEACHER", 12L,
            "未达到正式路演要求", evaluationId, null, 2
    ));

    assertThatThrownBy(() -> service.recordDecision(new RecordDecision(
            checkpointId, "PASSED", "TEACHER", 12L,
            "过期页面提交", evaluationId, null, 2
    ))).isInstanceOf(OptimisticLockingFailureException.class);
}

@Test
void revokingAutoPassAppendsDecisionAndReopensCheckpoint() {
    long checkpointId = autoPassedCheckpoint();
    long passDecisionId = repository.latestDecision(checkpointId).id();

    service.recordDecision(new RecordDecision(
            checkpointId, "REVOKED", "TEACHER", 12L,
            "抽查发现提交证据无效", null, passDecisionId, 3
    ));

    assertThat(repository.decisions(checkpointId)).hasSize(2);
    assertThat(repository.checkpoint(checkpointId).status()).isEqualTo("REOPENED");
}
```

- [ ] **Step 2: Run tests and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopServiceTest test
```

Expected: compilation failure because `RecordDecision` and decision methods do not exist.

- [ ] **Step 3: Add the decision command**

Add to `ClosedLoopCommands`:

```java
public record RecordDecision(
        Long checkpointId, String decisionType, String decisionSource,
        Long decidedBy, String reason, Long basedOnEvaluationId,
        Long supersedesDecisionId, int expectedCheckpointVersion
) {}
```

- [ ] **Step 4: Implement append-only decisions**

Add to `ClosedLoopService`:

```java
@Transactional
public long recordDecision(RecordDecision command) {
    if ("TEACHER".equals(command.decisionSource())
            && (command.reason() == null || command.reason().isBlank())) {
        throw new IllegalArgumentException("老师裁决必须填写原因");
    }
    CheckpointRow checkpoint = repository.checkpoint(command.checkpointId());
    CheckpointStatus next = switch (DecisionType.valueOf(command.decisionType())) {
        case PASSED -> PASSED;
        case FAILED, REWORK_REQUIRED -> FAILED;
        case REVOKED -> REOPENED;
    };
    if (!repository.compareAndSetCheckpoint(
            checkpoint.id(), checkpoint.status(), next.name(),
            command.expectedCheckpointVersion())) {
        throw new OptimisticLockingFailureException("检查点状态已变化，请刷新后重试");
    }
    return repository.insertDecision(command);
}
```

Do not add an update or delete method for `closed_loop_decision`.

- [ ] **Step 5: Run tests**

```bash
cd backend
mvn -Dtest=ClosedLoopServiceTest test
```

Expected: all `ClosedLoopServiceTest` tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopCommands.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopService.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopRepository.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopServiceTest.java
git commit -m "feat(closed-loop): add append-only decisions"
```

## Task 6: Generate and publish remediation drafts

- [ ] **Step 1: Write failing remediation tests**

Create `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopRemediationServiceTest.java`:

```java
@Test
void generateDraftsIsIdempotentAndPublishCreatesProjectTasksOnce() {
    long checkpointId = failedCheckpoint();
    List<IssueDraft> issues = List.of(new IssueDraft(
            "loss:business-value", "BUSINESS", "HIGH",
            "补充量化收益", "缺少量化收益证据",
            "ai-report:30/loss:business-value",
            "{\"anchorIds\":[11]}", "展示至少三项量化收益"
    ));

    long firstBatch = service.generateBatch(checkpointId, issues, "SYSTEM");
    long secondBatch = service.generateBatch(checkpointId, issues, "SYSTEM");
    assertThat(secondBatch).isEqualTo(firstBatch);

    service.publishBatch(firstBatch, new PublishBatch(
            12L, "确认发布", Map.of(
              "loss:business-value", new DraftOverride(
                List.of(7L), 7L, "2026-07-20T18:00:00",
                "ppt-task:107/page:5", "v3", "PPT_PAGE_QUALITY"
              )
            )
    ));
    service.publishBatch(firstBatch, samePublishCommand());

    assertThat(repository.taskLinks(firstBatch)).hasSize(1);
    verify(projectTeamService, times(1)).createTask(
            eq(9L), eq(3L), eq(12L), eq("TEACHER"), anyMap());
}
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopRemediationServiceTest test
```

Expected: compilation failure for missing remediation types.

- [ ] **Step 3: Add remediation commands**

Add records to `ClosedLoopCommands`:

```java
public record IssueDraft(
        String externalKey, String category, String severity,
        String title, String description, String sourceRef,
        String evidenceSnapshot, String acceptanceCriteria
) {}

public record DraftOverride(
        java.util.List<Long> assigneeUserIds, Long ownerUserId,
        String dueAt, String targetRef, String targetBaselineVersion,
        String recheckPolicy
) {}

public record PublishBatch(
        Long reviewerId, String reviewComment,
        java.util.Map<String, DraftOverride> overrides
) {}
```

- [ ] **Step 4: Implement generate and publish**

`ClosedLoopRemediationService.generateBatch` must:

```java
@Transactional
public long generateBatch(long checkpointId, List<IssueDraft> issueDrafts, String generatedBy) {
    CheckpointRow checkpoint = repository.checkpoint(checkpointId);
    long batchId = repository.findOrCreateBatch(
            checkpointId, checkpoint.cycleNo(), "SYSTEM_DRAFT", generatedBy);
    for (IssueDraft draft : issueDrafts) {
        long issueId = repository.findOrCreateIssue(checkpointId, checkpoint.cycleNo(), draft);
        repository.findOrCreateTaskDraft(batchId, issueId, draft);
    }
    repository.moveCheckpointToRemediating(checkpointId);
    return batchId;
}
```

`publishBatch` must:

```java
@Transactional
public void publishBatch(long batchId, PublishBatch command, Long tenantId, Long teamId) {
    for (TaskDraftRow draft : repository.unpublishedDrafts(batchId)) {
        DraftOverride override = command.overrides().get(draft.draftKey());
        Map<String, Object> body = Map.of(
                "title", draft.title(),
                "description", draft.description(),
                "taskType", "CLOSED_LOOP_REMEDIATION",
                "stageKey", repository.checkpoint(draft.checkpointId()).domainType(),
                "priority", draft.priority(),
                "ownerUserId", override.ownerUserId(),
                "assigneeUserIds", override.assigneeUserIds(),
                "dueAt", override.dueAt()
        );
        Map<String, Object> task = projectTeamService.createTask(
                teamId, tenantId, command.reviewerId(), "TEACHER", body);
        repository.linkTask(batchId, draft, ((Number) task.get("id")).longValue(), override);
    }
    repository.markBatchPublished(batchId, command.reviewerId(), command.reviewComment());
}
```

Before calling `createTask`, validate that every assignee is a member of the team and that `targetRef`, acceptance criteria and recheck policy are non-blank.

- [ ] **Step 5: Run remediation tests**

```bash
cd backend
mvn -Dtest=ClosedLoopRemediationServiceTest test
```

Expected: draft idempotency and single task creation tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopRemediationService.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopCommands.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopRepository.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopRemediationServiceTest.java
git commit -m "feat(closed-loop): publish reviewed remediation drafts"
```

## Task 7: Move accepted tasks to recheck without auto-passing

- [ ] **Step 1: Write the failing listener test**

Add to `ClosedLoopRemediationServiceTest`:

```java
@Test
void acceptedLastLinkedTaskMovesCheckpointOnlyToReadyForRecheck() {
    long checkpointId = remediationCheckpointWithTwoTasks();

    listener.onTaskAccepted(new ProjectTaskAcceptedEvent(41L, 9L, 101L, 12L));
    assertThat(repository.checkpoint(checkpointId).status()).isEqualTo("REMEDIATING");

    listener.onTaskAccepted(new ProjectTaskAcceptedEvent(42L, 9L, 102L, 12L));
    assertThat(repository.checkpoint(checkpointId).status()).isEqualTo("READY_FOR_RECHECK");
    assertThat(repository.checkpoint(checkpointId).status()).isNotEqualTo("PASSED");
}
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopRemediationServiceTest test
```

Expected: missing event/listener compilation failure.

- [ ] **Step 3: Create the event and listener**

Create `ProjectTaskAcceptedEvent.java`:

```java
package com.orep.backend.service.closedloop;

public record ProjectTaskAcceptedEvent(
        Long taskId, Long teamId, Long submissionId, Long reviewedBy
) {}
```

Create `ClosedLoopTaskEventListener.java`:

```java
package com.orep.backend.service.closedloop;

import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class ClosedLoopTaskEventListener {
    private final ClosedLoopRepository repository;

    public ClosedLoopTaskEventListener(ClosedLoopRepository repository) {
        this.repository = repository;
    }

    @EventListener
    @Transactional
    public void onTaskAccepted(ProjectTaskAcceptedEvent event) {
        repository.markLinkedTaskAccepted(event.taskId(), event.submissionId(), event.reviewedBy());
        for (Long checkpointId : repository.checkpointsLinkedToTask(event.taskId())) {
            if (repository.allLinkedTasksAccepted(checkpointId)) {
                repository.moveCheckpointToReadyForRecheck(checkpointId);
                repository.markIssuesReadyForRecheck(checkpointId);
            }
        }
    }
}
```

- [ ] **Step 4: Publish the event from existing task review**

Modify `ProjectTeamService` constructor to accept `ApplicationEventPublisher eventPublisher`, store it, and after line 1034 add:

```java
if ("APPROVED".equals(status)) {
    eventPublisher.publishEvent(new ProjectTaskAcceptedEvent(
            taskId, teamId, submissionId, userId));
}
```

Do not publish an accepted event for `REJECTED` or `CHANGES_REQUESTED`.

- [ ] **Step 5: Run listener and ProjectTeam regression tests**

```bash
cd backend
mvn -Dtest=ClosedLoopRemediationServiceTest,ProjectTeamControllerTest test
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/closedloop/ProjectTaskAcceptedEvent.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopTaskEventListener.java backend/src/main/java/com/orep/backend/service/ProjectTeamService.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopRemediationServiceTest.java
git commit -m "feat(closed-loop): return accepted tasks to domain recheck"
```

## Task 8: Expose access-controlled APIs

- [ ] **Step 1: Write failing MockMvc tests**

Create `backend/src/test/java/com/orep/backend/controller/ClosedLoopControllerTest.java`:

```java
@Test
void teacherCanRecordDecisionAndStaleVersionReturnsConflict() throws Exception {
    when(access.canFinalDecide(3L, 9L, 12L, "TEACHER")).thenReturn(true);
    when(service.recordDecision(any())).thenThrow(
            new OptimisticLockingFailureException("检查点状态已变化，请刷新后重试"));

    mvc.perform(post("/api/closed-loop/checkpoints/31/decisions")
            .requestAttr("tenantId", 3L)
            .requestAttr("userId", 12L)
            .requestAttr("role", "TEACHER")
            .contentType(MediaType.APPLICATION_JSON)
            .content("""
              {"teamId":9,"decisionType":"FAILED","reason":"未达到要求",
               "basedOnEvaluationId":44,"expectedCheckpointVersion":2}
              """))
       .andExpect(status().isConflict());
}
```

Also add a test asserting STUDENT receives 403 when calling the same endpoint.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopControllerTest test
```

Expected: missing controller/access service failure.

- [ ] **Step 3: Implement access checks**

Create `ClosedLoopAccessService`:

```java
public boolean canFinalDecide(Long tenantId, Long teamId, Long userId, String role) {
    if ("ADMIN".equals(role) || "SCHOOL_ADMIN".equals(role) || "TEACHER".equals(role)) {
        return repository.teamBelongsToTenant(teamId, tenantId);
    }
    return false;
}

public void assertTeamAccess(Long tenantId, Long teamId, Long userId, String role) {
    if (!repository.userCanAccessTeam(tenantId, teamId, userId, role)) {
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该项目团队闭环");
    }
}
```

- [ ] **Step 4: Implement controller endpoints**

Create `ClosedLoopController` with:

```java
@PostMapping("/checkpoints/{checkpointId}/decisions")
public Result<Map<String, Object>> decide(
        @PathVariable Long checkpointId,
        @RequestBody DecisionRequest body,
        HttpServletRequest request
) {
    Long tenantId = (Long) request.getAttribute("tenantId");
    Long userId = (Long) request.getAttribute("userId");
    String role = String.valueOf(request.getAttribute("role"));
    if (!access.canFinalDecide(tenantId, body.teamId(), userId, role)) {
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "仅老师可做最终裁决");
    }
    long id = service.recordDecision(body.toCommand(checkpointId, userId));
    return Result.success(Map.of("decisionId", id));
}
```

Add exception mapping for `OptimisticLockingFailureException` in the controller or `GlobalExceptionHandler`:

```java
@ExceptionHandler(OptimisticLockingFailureException.class)
public ResponseEntity<Result<Void>> conflict(OptimisticLockingFailureException error) {
    return ResponseEntity.status(409).body(Result.error(409, error.getMessage()));
}
```

Expose:

- `POST /api/closed-loop/checkpoints`
- `POST /api/closed-loop/checkpoints/{id}/evaluations`
- `POST /api/closed-loop/checkpoints/{id}/decisions`
- `POST /api/closed-loop/checkpoints/{id}/remediation-batches`
- `POST /api/closed-loop/remediation-batches/{id}/publish`
- `GET /api/closed-loop/teams/{teamId}/summary`
- `GET /api/closed-loop/teams/{teamId}/review-inbox`

- [ ] **Step 5: Run controller tests**

```bash
cd backend
mvn -Dtest=ClosedLoopControllerTest,GlobalExceptionHandlerTest test
```

Expected: teacher success/409 mapping and student 403 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/controller/ClosedLoopController.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopAccessService.java backend/src/main/java/com/orep/backend/dto/closedloop/ClosedLoopRequests.java backend/src/main/java/com/orep/backend/controller/GlobalExceptionHandler.java backend/src/test/java/com/orep/backend/controller/ClosedLoopControllerTest.java
git commit -m "feat(closed-loop): expose guarded core APIs"
```

## Task 9: Run the phase-one verification

- [ ] **Step 1: Run all closed-loop tests**

```bash
cd backend
mvn -Dtest='*ClosedLoop*Test' test
```

Expected: all closed-loop tests pass.

- [ ] **Step 2: Run affected regression tests**

```bash
cd backend
mvn -Dtest=ProjectTeamControllerTest,ExamServiceTest,AiScoreRemediationServiceTest test
```

Expected: all selected tests pass.

- [ ] **Step 3: Run the full backend suite**

```bash
cd backend
mvn test
```

Expected: build success, failures 0, errors 0.

- [ ] **Step 4: Verify flags default to off**

```bash
cd backend
rg -n "OREP_CLOSED_LOOP_ENABLED:false|enabled: \\$\\{OREP_CLOSED_LOOP_ENABLED:false\\}" src/main/resources/application.yml
```

Expected: one default-off configuration match.

- [ ] **Step 5: Commit verification notes**

Create `docs/superpowers/reports/2026-07-17-closed-loop-phase-1-verification.md` with the exact commands, test counts and any skipped environmental checks, then:

```bash
git add docs/superpowers/reports/2026-07-17-closed-loop-phase-1-verification.md
git commit -m "docs(closed-loop): record phase one verification"
```
