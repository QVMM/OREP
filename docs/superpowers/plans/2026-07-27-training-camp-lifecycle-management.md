# 集训营生命周期管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让有权限的教师安全调整无提交集训的开始日期，并可归档或彻底删除集训。

**Architecture:** 在现有 `TeacherPortalService` 中增加事务级改期与删除方法，由控制器暴露教师专用接口。改期通过统一日期偏移同步集训、周、训练日和关联任务；删除提供归档和永久清除两种模式。教师端在集训概览页提供管理菜单与确认弹窗。

**Tech Stack:** Java 21、Spring Boot、JdbcTemplate、JUnit 5、Vue 3、Element Plus、Vite、Docker Compose

---

### Task 1: 后端改期行为

**Files:**
- Create: `backend/src/test/java/com/orep/backend/service/TeacherPortalCampLifecycleTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/TeacherPortalService.java`

- [ ] **Step 1: 写改期失败测试**

测试用 H2 建立最小集训表结构和一组集训、周、训练日、关联任务数据，覆盖：

```java
@Test
void rescheduleMovesCampWeeksDaysAndTasksByTheSameOffset() {
    Map<String, Object> result = service.rescheduleCamp(
            1L, 9L, "TEACHER", 101L, Map.of("startDate", "2026-07-27"));
    assertThat(result.get("startDate")).isEqualTo(LocalDate.of(2026, 7, 27));
    assertThat(date("training_day", 1001L, "training_date"))
            .isEqualTo(LocalDate.of(2026, 7, 27));
    assertThat(dateTime("project_task", 2001L, "due_at"))
            .isEqualTo(LocalDateTime.of(2026, 7, 27, 22, 0));
}

@Test
void rescheduleRejectsCampWithSubmissions() {
    insertSubmissionForCamp(101L);
    assertThatThrownBy(() -> service.rescheduleCamp(
            1L, 9L, "TEACHER", 101L, Map.of("startDate", "2026-07-27")))
            .isInstanceOf(ResponseStatusException.class)
            .hasMessageContaining("已有学生提交");
}

@Test
void rescheduleRejectsOverlappingCamp() {
    insertOverlappingCamp();
    assertThatThrownBy(() -> service.rescheduleCamp(
            1L, 9L, "TEACHER", 101L, Map.of("startDate", "2026-07-27")))
            .isInstanceOf(ResponseStatusException.class)
            .hasMessageContaining("已有集训营");
}
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd backend && mvn -Dtest=TeacherPortalCampLifecycleTest test`

Expected: FAIL，提示 `rescheduleCamp` 尚不存在。

- [ ] **Step 3: 实现事务级日期平移**

新增方法：

```java
@Transactional
public Map<String, Object> rescheduleCamp(
        Long tenantId, Long userId, String role, Long campId, Map<String, Object> body)
```

实现顺序：

```text
1. 读取集训及总天数，并通过关联团队执行 assertTeamAccess。
2. 查询 training_day_task -> project_task_submission；数量大于 0 时拒绝改期。
3. 计算新结束日期并检查同团队其他 PLANNED/ACTIVE 集训重叠。
4. 更新 training_camp 的 start_date、end_date 和状态。
5. 按 day_no 重算 training_day.training_date，due_at 保留原时间，early_unlocked_at 置空。
6. 按 week_no 重算 training_camp_week 日期。
7. 同步 training_day_task 关联的 project_task.start_at 和 due_at。
8. 记录 CAMP_RESCHEDULED 教师操作事件并返回 campOverview。
```

- [ ] **Step 4: 运行后端改期测试**

Run: `cd backend && mvn -Dtest=TeacherPortalCampLifecycleTest test`

Expected: PASS。

### Task 2: 后端归档与永久删除

**Files:**
- Modify: `backend/src/test/java/com/orep/backend/service/TeacherPortalCampLifecycleTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/TeacherPortalService.java`

- [ ] **Step 1: 写归档与删除失败测试**

```java
@Test
void archiveOnlyChangesCampVisibilityStatus() {
    service.deleteCamp(1L, 9L, "TEACHER", 101L, Map.of("mode", "ARCHIVE"));
    assertThat(text("training_camp", 101L, "status")).isEqualTo("ARCHIVED");
    assertThat(count("training_day", "camp_id", 101L)).isEqualTo(2);
    assertThat(count("project_task_submission", "task_id", 2001L)).isEqualTo(1);
}

@Test
void purgeRequiresExactCampName() {
    assertThatThrownBy(() -> service.deleteCamp(
            1L, 9L, "TEACHER", 101L,
            Map.of("mode", "PURGE", "confirmationName", "错误名称")))
            .isInstanceOf(ResponseStatusException.class)
            .hasMessageContaining("集训名称");
}

@Test
void purgeDeletesCampOwnedGraphButKeepsTeamAndUsers() {
    service.deleteCamp(1L, 9L, "TEACHER", 101L,
            Map.of("mode", "PURGE", "confirmationName", "第一阶段集训"));
    assertThat(count("training_camp", "id", 101L)).isZero();
    assertThat(count("training_day", "camp_id", 101L)).isZero();
    assertThat(count("project_task", "id", 2001L)).isZero();
    assertThat(count("project_team", "id", 301L)).isEqualTo(1);
    assertThat(count("users", "id", 401L)).isEqualTo(1);
}
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `cd backend && mvn -Dtest=TeacherPortalCampLifecycleTest test`

Expected: FAIL，提示 `deleteCamp` 尚不存在或关联数据未清理。

- [ ] **Step 3: 实现归档与永久删除**

新增方法：

```java
@Transactional
public Map<String, Object> deleteCamp(
        Long tenantId, Long userId, String role, Long campId, Map<String, Object> body)
```

归档执行：

```sql
UPDATE training_camp SET status='ARCHIVED' WHERE id=? AND tenant_id=?
```

永久删除先校验完整名称，再收集训练日、任务和文件标识，按依赖顺序删除：

```text
任务批改与提交附件 -> 项目任务提交 -> 任务要求 -> 训练日任务关系
-> 集训专属项目任务 -> 训练日学习记录/资源/附件
-> 训练日 -> 集训周 -> 集训团队关系 -> 集训营
```

只删除通过当前 `campId` 找到的集训专属任务；团队、成员、用户以及其他模块数据不进入删除语句。

- [ ] **Step 4: 运行生命周期测试**

Run: `cd backend && mvn -Dtest=TeacherPortalCampLifecycleTest test`

Expected: PASS。

### Task 3: 教师接口

**Files:**
- Modify: `backend/src/test/java/com/orep/backend/controller/TeacherPortalControllerTest.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/TeacherPortalController.java`

- [ ] **Step 1: 写接口契约测试**

```java
mockMvc.perform(patch("/api/teacher/portal/camps/101/schedule")
        .contentType(APPLICATION_JSON)
        .content("{\"startDate\":\"2026-07-27\"}"))
        .andExpect(status().isOk());

mockMvc.perform(delete("/api/teacher/portal/camps/101")
        .contentType(APPLICATION_JSON)
        .content("{\"mode\":\"PURGE\",\"confirmationName\":\"第一阶段集训\"}"))
        .andExpect(status().isOk());
```

- [ ] **Step 2: 运行接口测试并确认失败**

Run: `cd backend && mvn -Dtest=TeacherPortalControllerTest test`

Expected: FAIL，接口返回 404。

- [ ] **Step 3: 增加控制器路由**

```java
@PatchMapping("/camps/{campId}/schedule")
public Result<Map<String,Object>> rescheduleCamp(
        @PathVariable Long campId,
        @RequestBody Map<String,Object> body,
        HttpServletRequest request) {
    return Result.success(service.rescheduleCamp(
            tenantId(request), userId(request), role(request), campId, body));
}

@DeleteMapping("/camps/{campId}")
public Result<Map<String,Object>> deleteCamp(
        @PathVariable Long campId,
        @RequestBody Map<String,Object> body,
        HttpServletRequest request) {
    return Result.success(service.deleteCamp(
            tenantId(request), userId(request), role(request), campId, body));
}
```

- [ ] **Step 4: 运行控制器测试**

Run: `cd backend && mvn -Dtest=TeacherPortalControllerTest test`

Expected: PASS。

### Task 4: 教师端管理交互

**Files:**
- Create: `frontend/teacher/tests/camp-lifecycle-contract.test.mjs`
- Modify: `frontend/teacher/src/api/index.js`
- Modify: `frontend/teacher/src/views/camp/CampOverviewView.vue`

- [ ] **Step 1: 写教师端契约失败测试**

测试源码必须包含：

```js
assert.match(source, /管理集训/)
assert.match(source, /调整开始日期/)
assert.match(source, /归档保留记录/)
assert.match(source, /彻底删除全部信息/)
assert.match(source, /confirmationName/)
assert.match(source, /已有学生提交，不能直接改期/)
```

- [ ] **Step 2: 运行教师端测试并确认失败**

Run: `cd frontend/teacher && node --test tests/camp-lifecycle-contract.test.mjs`

Expected: FAIL，管理入口和接口尚不存在。

- [ ] **Step 3: 增加 API 方法**

```js
export async function rescheduleTeacherCamp(campId, startDate) {
  return unwrap(await request.patch(
    `/api/teacher/portal/camps/${campId}/schedule`, { startDate })) || {}
}

export async function deleteTeacherCamp(campId, payload) {
  return unwrap(await request.delete(
    `/api/teacher/portal/camps/${campId}`, { data: payload })) || {}
}
```

- [ ] **Step 4: 增加管理菜单和弹窗**

在概览页加入：

```text
管理集训
├── 调整开始日期：日期输入、原/新日期预览、提交保护提示
└── 删除集训
    ├── 归档保留记录
    └── 彻底删除全部信息：输入完整集训名称
```

成功改期后重新加载当前集训；归档或永久删除后刷新上下文并跳转 `/camp`。

- [ ] **Step 5: 运行前端测试和构建**

Run: `cd frontend/teacher && node --test tests/camp-lifecycle-contract.test.mjs && npm run build`

Expected: 测试 PASS，Vite 构建成功。

### Task 5: 全量验证、备份和云端发布

**Files:**
- Update artifact: `deploy/backend/orep-backend-1.0.0.jar`
- Update artifact: `deploy/frontend/teacher/dist`

- [ ] **Step 1: 运行完整测试**

Run: `cd backend && mvn test`

Expected: 所有测试通过。

Run: `cd frontend/teacher && node --test tests/*.test.mjs && npm run build`

Expected: 所有测试通过并成功构建。

- [ ] **Step 2: 打包并同步本地发布目录**

Run: `cd backend && mvn -DskipTests package`

Expected: 生成 `target/orep-backend-1.0.0.jar`。

将教师端 `dist` 和后端 JAR 同步到 `deploy` 发布目录。

- [ ] **Step 3: 云端备份**

在 `/opt/orep/backups/camp-lifecycle-<timestamp>` 保存：

```text
当前后端 JAR
当前教师端静态文件
training_camp、training_camp_week、training_camp_team、training_day、
training_day_task、project_task、project_task_requirement、
project_task_submission 相关数据库备份
```

- [ ] **Step 4: 仅更新后端和教师端**

上传新的 JAR 和教师端静态文件，重新构建并启动：

```text
backend
frontend-teacher
nginx（仅在容器地址刷新需要时重载）
```

不覆盖资源目录，不导入或重建数据库。

- [ ] **Step 5: 线上验证**

验证：

```text
教师端 /teacher/ 和 /teacher/camp 返回 200
未登录访问新接口返回 401
容器均为 Up
后端启动日志无异常
线上教师端资源包含“管理集训”“调整开始日期”“彻底删除全部信息”
```
