# 资源中心拆分与全局协作工作台实施计划

日期：2026-07-30  
依据规格：`docs/specs/2026-07-30-resource-center-global-collaboration-design.md`  
状态：待执行  
原则：分阶段交付、先契约后实现、每阶段可独立验证与回滚

## 1. 实施结果

完成后：

1. 学生端“文件中心”成为主导航中的“资源中心”。
2. `/project-team/files` 无损跳转到 `/resource-center`。
3. `/project-team` 保留为完整协作台。
4. 学生端和教师端左下出现特殊协作入口。
5. 移动端使用中央凸起协作入口和底部抽屉。
6. 学生可以向同团队成员发起协调，并完成接受、执行、提交、确认闭环。
7. 教师可以在浮窗内切换团队、发布任务和审核成果。
8. 协作待办通过现有 WebSocket 通道实时更新。
9. 新协作任务只有审核通过的选定成果才同步到资源中心。

## 2. 现有代码约束

### 2.1 学生端

- 主导航配置：`frontend/user/src/composables/apple/useOrepNavigation.js`
- 桌面导航：`frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- 移动导航：`frontend/user/src/components/workspace/WorkspaceMobileNav.vue`
- 工作台全局挂载点：`frontend/user/src/components/workspace/WorkspaceShell.vue`
- 当前文件中心页面：`frontend/user/src/views/ScriptList.vue`
- 当前完整协作台：`frontend/user/src/views/ProjectTeam.vue`
- 当前资源路由 `/resources` 已被 PPT 模板占用，不能复用。
- 当前 WebSocket 单例对同一 destination 只保留一个 callback；增加协作监听前必须改为多订阅分发。

### 2.2 教师端

- 全局壳层：`frontend/teacher/src/components/TeacherShell.vue`
- 导航配置：`frontend/teacher/src/config/nav.js`
- 团队任务 API 已存在于 `frontend/teacher/src/api/index.js`
- 教师端尚未安装 STOMP/SockJS，也没有通知客户端。
- 教师端资源中心 `/resources` 已存在，不需要迁移。

### 2.3 后端

- 项目任务集中在 `ProjectTeamService`，使用 `JdbcTemplate` 和 Map 结果。
- 普通学生当前不能创建任务，也不能审核提交。
- 当前审核权限只允许管理员、团队教师和有权限的队长。
- 当前 `sync_to_material=1` 时在提交阶段立即生成材料。
- 当前通知服务只识别 `REMINDER_SENT`，标题和目标地址也是训练营硬编码。
- Flyway 最新迁移为 `V106`，本功能从 `V107` 开始。

## 3. 阶段与依赖

```text
阶段一：资源中心与入口外壳
  └─ 不依赖新后端数据

阶段二：学生协调闭环
  ├─ V107 数据库迁移
  ├─ 通知服务泛化
  ├─ 协调请求服务与接口
  ├─ 项目任务权限扩展
  └─ 学生协作浮窗

阶段三：教师工作台与上线加固
  ├─ 复用阶段二聚合接口
  ├─ 复用现有教师任务发布与审核
  ├─ 教师实时通知客户端
  └─ E2E、灰度、监控与线上验证
```

迁移顺序：

1. 先部署向前兼容的数据库与后端。
2. 再部署学生端。
3. 最后部署教师端。
4. 功能开关默认关闭，完成验证后按租户开启。

## 4. 阶段一：资源中心与入口外壳

### 任务 1：建立资源中心路由契约

新增：

- `frontend/user/tests/resource-center-navigation-contract.test.mjs`

修改：

- `frontend/user/src/router/index.js`

测试先覆盖：

- `/resource-center` 使用当前 `ScriptList.vue`。
- `/project-team/files` 跳转到 `/resource-center`。
- 跳转保留 `teamId`、搜索和筛选查询参数。
- `/script-editor?tab=materials` 跳转到 `/resource-center`。
- `/resources` 仍然指向 PPT 模板页。

实现：

1. 增加 `ResourceCenter` 路由，组件继续复用 `ScriptList.vue`。
2. 将旧 `ProjectFiles` 路由改为 redirect 函数。
3. 将脚本编辑器 materials 兼容跳转更新到新路由。
4. 不复制 `ScriptList.vue`，保证新旧入口共用同一份文件数据与交互。

验证：

```bash
cd frontend/user
node --test tests/resource-center-navigation-contract.test.mjs
npm run build
```

### 任务 2：更新学生端导航分组与资源图标

修改：

- `frontend/user/src/composables/apple/useOrepNavigation.js`
- `frontend/user/src/components/workspace/WorkspaceModuleIcon.vue`
- `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- `frontend/user/src/components/workspace/WorkspaceMobileNav.vue`
- `frontend/user/tests/workspace-sidebar-navigation.spec.js`

实现：

1. 桌面普通导航删除 `/project-team` 协作项。
2. 新增 `/resource-center`，label 为“资源中心”，group 为 `resources`。
3. `resolveOrepRouteGroup`：
   - `/resource-center` → `resources`；
   - `/project-team` 继续返回内部 `collaboration` 分组，但不对应普通导航项；
   - `/resources` 继续属于 `aiApps`。
4. 为 `resources` 增加文件夹型 outline 和 filled 图标。
5. 桌面普通导航保持六项：
   - 首页；
   - 训练营；
   - 路演训练；
   - 资源中心；
   - AI 应用中心；
   - 我的。
6. 移动底部导航最多保留五个普通入口，加一个协作中央入口；不得生成七等分布局。
7. 移动端 AI 应用中心不占固定 dock 槽位，路由和首页入口继续保留。

验证：

```bash
cd frontend/user
npx playwright test tests/workspace-sidebar-navigation.spec.js
npm run build
```

### 任务 3：移除协作二级导航并迁移所有旧文件链接

修改：

- `frontend/user/src/components/workspace/WorkspaceShell.vue`
- `frontend/user/src/components/workspace/WorkspaceModuleNav.vue`
- `frontend/user/src/components/workspace/WorkspaceTopbar.vue`
- `frontend/user/src/modules/home/StudentHome.vue`
- `frontend/user/src/views/Dashboard.vue`
- `frontend/user/src/views/ScriptList.vue`
- `frontend/user/tests/collaboration-pages-design.spec.js`
- `frontend/user/tests/workspace-route-shell-stability.spec.js`

实现：

1. `/project-team` 不再触发 230px 协作二级导航。
2. 工作台壳层恢复两列：主导航 + 内容区。
3. 如果 `WorkspaceModuleNav.vue` 已无引用，删除其挂载；文件本身在最终清理时再删除。
4. 全局搜索：
   - “文件中心”改为“资源中心”；
   - 路径改为 `/resource-center`；
   - “任务管理”可继续指向完整协作台。
5. 首页和仪表盘中的旧材料链接全部更新。
6. `ScriptList.vue` 页面标题改为“资源中心”。
7. `ScriptList.vue` 内部 replace/push 不再写回旧文件路由。

搜索验收：

```bash
rg -n "/project-team/files|文件中心" frontend/user/src
```

只允许保留：

- 路由兼容定义；
- 明确说明旧名称的测试或注释。

验证：

```bash
cd frontend/user
npx playwright test \
  tests/collaboration-pages-design.spec.js \
  tests/workspace-route-shell-stability.spec.js
npm run build
```

### 任务 4：增加特殊协作入口外壳

新增：

- `frontend/user/src/components/collaboration/CollaborationBrandMark.vue`
- `frontend/user/src/components/collaboration/CollaborationEntryButton.vue`
- `frontend/user/src/stores/collaboration.js`
- `frontend/user/tests/collaboration-entry-shell.spec.js`

修改：

- `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- `frontend/user/src/components/workspace/WorkspaceMobileNav.vue`
- `frontend/user/src/components/workspace/WorkspaceShell.vue`
- `frontend/user/src/styles/workspace-tokens.css`（只有确实缺少组件 token 时修改）

阶段一实现：

1. Pinia store 先提供：
   - `isOpen`；
   - `open()`；
   - `close()`；
   - `toggle()`；
   - `actionCount`。
2. 桌面入口固定在普通导航下方、侧栏底部。
3. 移动端入口占中央特殊位置。
4. 彩色只在四格协作标识中使用。
5. 功能尚未开启时，点击进入 `/project-team`，不显示死按钮。
6. `VITE_COLLABORATION_ENABLED=true` 时才打开浮窗容器。

验证：

- 桌面入口不随普通导航滚动消失。
- 390px 下无七列压缩。
- 焦点、可访问名称和徽标说明正确。

## 5. 阶段二：后端学生协调闭环

### 任务 5：新增数据库迁移

新增：

- `backend/src/main/resources/db/migration/V107__global_collaboration_requests.sql`
- `backend/src/test/java/com/orep/backend/service/CollaborationMigrationContractTest.java`

迁移内容：

1. 新建 `collaboration_request`。
2. 增加 `idempotency_key`，并建立 `tenant_id + requester_id + idempotency_key` 唯一索引。
3. `project_task` 增加：
   - `source_type VARCHAR(40) NOT NULL DEFAULT 'OTHER'`；
   - `reviewer_user_id BIGINT NULL`。
4. 为协调请求建立：
   - 租户/团队/状态索引；
   - 接收人/状态/时间索引；
   - 发起人/状态/时间索引；
   - `linked_task_id` 唯一索引。
5. 为任务建立：
   - `source_type` 索引；
   - `reviewer_user_id` 索引。
6. 为延迟资源同步增加稳定来源键：
   - `project_material.source_submission_id`；
   - `project_material.source_item_key`；
   - `source_item_key` 唯一索引。
7. 所有新增字段必须有兼容默认值，既有任务不需要业务回填。

测试：

- SQL 包含必要字段、默认值、索引和表名。
- 迁移编号唯一。
- H2 服务测试的临时 schema 与迁移字段保持一致。

验证：

```bash
cd backend
mvn -Dtest=CollaborationMigrationContractTest test
```

### 任务 6：将通知服务从训练提醒泛化为平台通知

修改：

- `backend/src/main/java/com/orep/backend/service/NotificationService.java`
- `backend/src/test/java/com/orep/backend/service/NotificationServiceTest.java`
- `backend/src/main/java/com/orep/backend/controller/NotificationController.java`（只有查询契约需要时修改）
- `backend/src/test/java/com/orep/backend/controller/NotificationControllerTest.java`

实现：

1. 新增通用方法：

```java
createNotification(
    Long tenantId,
    Long actorUserId,
    Long recipientUserId,
    String eventType,
    String targetType,
    Map<String, Object> payload
)
```

2. `createReminder` 保留为兼容包装，不改教师提醒调用方。
3. 通知查询按明确的用户通知事件白名单读取，不扩大到 `teacher_portal_event` 中的其他业务事件。
4. 标题、消息、目标路径和协作实体 ID 从受控 payload 映射。
5. 服务端定义允许的协作事件类型，拒绝任意事件名写入。
6. `markRead` 和 `markAllRead` 支持所有用户通知事件。
7. WebSocket destination 保持：

```text
/user/queue/notifications
```

8. 协作通知失败不得回滚协调核心事务；失败要记录并可重试。

回归：

- 原训练提醒标题、路径和已读逻辑保持。
- 顶部通知中心仍能展示提醒。

验证：

```bash
cd backend
mvn -Dtest=NotificationServiceTest,NotificationControllerTest test
```

### 任务 7：实现协调请求服务

新增：

- `backend/src/main/java/com/orep/backend/service/CollaborationService.java`
- `backend/src/main/java/com/orep/backend/service/CollaborationNotificationListener.java`
- `backend/src/test/java/com/orep/backend/service/CollaborationServiceTest.java`

服务职责：

- 汇总徽标和标签数量；
- 查询学生与教师工作台条目；
- 创建协调请求；
- 读取请求详情；
- 接受；
- 婉拒；
- 撤回；
- 验证同租户、同团队和成员有效性；
- 调用通知服务；
- 管理状态冲突和幂等。

创建请求规则：

1. 发起人必须是团队有效成员。
2. 接收人必须是同团队有效成员。
3. 不能邀请自己。
4. 标题、说明、截止时间和优先级服务端校验。
5. 接受 `Idempotency-Key` 请求头或 body 中等价键。
6. 同一幂等键只创建一个请求。

接受规则：

1. 方法使用 `@Transactional`。
2. `SELECT ... FOR UPDATE` 锁定请求。
3. 状态不是 `PENDING` 时：
   - 已接受：返回现有任务；
   - 其他状态：返回 `409 CONFLICT`。
4. 再次校验双方成员关系。
5. 创建正式任务、负责人和审核人。
6. 写回 `linked_task_id` 和 `responded_at`。
7. 通过 Spring 业务事件发布协作结果。
8. `CollaborationNotificationListener` 使用事务提交后监听发送通知；发送失败记录补偿信息，不回滚核心事务。

查询规则：

- 学生只能看到本人参与或团队管理范围内的请求。
- 教师只能按管理范围查询。
- summary 只统计需要当前用户操作的事项。
- 列表使用稳定排序和分页。

验证：

```bash
cd backend
mvn -Dtest=CollaborationServiceTest test
```

### 任务 8：增加协作 API 控制器

新增：

- `backend/src/main/java/com/orep/backend/controller/CollaborationController.java`
- `backend/src/test/java/com/orep/backend/controller/CollaborationControllerTest.java`

修改：

- `backend/src/main/resources/application.yml`

接口：

```text
GET  /api/collaboration/summary
GET  /api/collaboration/items
POST /api/collaboration/requests
GET  /api/collaboration/requests/{id}
POST /api/collaboration/requests/{id}/accept
POST /api/collaboration/requests/{id}/decline
POST /api/collaboration/requests/{id}/withdraw
```

要求：

- 从请求属性读取 tenant、user、role，保持现有控制器风格。
- 不接受客户端传入 tenantId 或 actorUserId。
- 所有状态冲突返回 409。
- 无权限返回 403。
- 不存在或不可见使用统一的 404/403 策略，避免泄露数据。
- 功能关闭时返回 404 或明确未启用响应。

功能开关：

```yaml
orep:
  features:
    collaboration:
      enabled: ${OREP_COLLABORATION_ENABLED:false}
```

验证：

```bash
cd backend
mvn -Dtest=CollaborationControllerTest test
```

### 任务 9：扩展正式任务创建与审核权限

修改：

- `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceReviewTest.java`
- `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceMembershipTest.java`

实现：

1. 增加仅供服务层调用的 `createAcceptedCollaborationTask`：
   - `source_type='PEER_COLLABORATION'`；
   - `stage_key='COLLABORATION'`；
   - `created_by=requesterId`；
   - `owner_user_id=recipientId`；
   - 写入 assignee；
   - `reviewer_user_id=requesterId`。
2. 该方法不直接暴露为学生创建任务接口。
3. 修改审核授权：
   - 既有管理员、教师、队长权限保持；
   - 只有 `PEER_COLLABORATION` 任务的 `reviewer_user_id` 可以额外审核；
   - 其他任务不能借此获得学生审核权限。
4. `reviewSubmission` 必须把 taskId 传入权限校验。
5. 协调任务的提交权限继续使用现有 owner/assignee 判断。
6. 被移出团队后不能继续提交或审核。

验证：

```bash
cd backend
mvn -Dtest=ProjectTeamServiceReviewTest,ProjectTeamServiceMembershipTest test
```

### 任务 10：仅对新协作任务延迟同步资源

修改：

- `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceReviewTest.java`

实现：

1. `submitTask` 读取任务 `sourceType`。
2. `PEER_COLLABORATION` 和 `TEACHER_ASSIGNMENT`：
   - 保存 `sync_to_material` 意愿；
   - 提交阶段不创建 `project_material`。
3. 既有 `TRAINING`、`OTHER` 和历史任务保持当前提交时同步语义。
4. 审核状态为 `APPROVED` 且 `sync_to_material=1` 时：
   - 查询该 submission 的 assets 和 links；
   - 同步到资源中心；
   - `review_status='APPROVED'`；
   - 写入 `source_submission_id` 与稳定 `source_item_key`。
5. 通过唯一来源键保证补偿重试不产生重复材料。
6. `CHANGES_REQUESTED` 和 `REJECTED` 不同步。

验证：

- 既有即时同步测试保持通过。
- 新增协作延迟同步测试。
- 重复补偿不会重复创建材料。

## 6. 阶段二：学生端协作工作台

### 任务 11：修复学生端 WebSocket 多订阅能力

修改：

- `frontend/user/src/utils/websocket.js`
- `frontend/user/src/services/notificationClient.js`
- `frontend/user/tests/notification-center.spec.js`

新增：

- `frontend/user/tests/websocket-multisubscriber-contract.test.mjs`

实现：

1. `subscriptions` 从 `destination → callback` 改为：

```text
destination → {
  activeSubscription,
  callbacks: Map<subscriberId, callback>
}
```

2. 同一 destination 只建立一条 STOMP subscription。
3. 消息按顺序分发给所有 callback。
4. `subscribe()` 返回唯一取消 token。
5. `unsubscribe(token)` 只移除当前调用方。
6. 最后一个 callback 移除后才取消底层 STOMP subscription。
7. 重连时每个 destination 只恢复一次。
8. 顶部通知中心和协作 store 可以同时监听。

验证：

```bash
cd frontend/user
node --test tests/websocket-multisubscriber-contract.test.mjs
npx playwright test tests/notification-center.spec.js
```

### 任务 12：增加学生协作 API 客户端与全局 store

新增：

- `frontend/user/src/services/collaborationClient.js`
- `frontend/user/tests/collaboration-store-contract.test.mjs`

修改：

- `frontend/user/src/stores/collaboration.js`

客户端方法：

- `fetchSummary()`；
- `fetchItems(view, teamId, cursor)`；
- `createRequest(payload, idempotencyKey)`；
- `fetchRequest(id)`；
- `acceptRequest(id)`；
- `declineRequest(id, reason)`；
- `withdrawRequest(id)`。

store 状态：

- `isOpen`；
- `activeTab`；
- `activeTeamId`；
- `navigationStack`；
- `drafts`；
- `scrollPositions`；
- `summary`；
- `itemsByTab`；
- `loadingByTab`；
- `errorByTab`；
- `lastRefreshedAt`。

行为：

1. 有 action required 时默认收件箱，否则进行中。
2. 路由变化不重置。
3. 页面 focus 时刷新 summary。
4. 收到协作通知时刷新 summary 和受影响标签。
5. 不覆盖正在编辑的草稿。
6. 退出登录时清空。
7. 团队失效时清理对应详情与草稿。

### 任务 13：实现学生协作浮窗组件

新增：

- `frontend/user/src/components/collaboration/CollaborationHub.vue`
- `frontend/user/src/components/collaboration/CollaborationHeader.vue`
- `frontend/user/src/components/collaboration/CollaborationTabs.vue`
- `frontend/user/src/components/collaboration/CollaborationItemList.vue`
- `frontend/user/src/components/collaboration/CollaborationItemRow.vue`
- `frontend/user/src/components/collaboration/CollaborationRequestForm.vue`
- `frontend/user/src/components/collaboration/CollaborationDetail.vue`
- `frontend/user/src/components/collaboration/CollaborationEmptyState.vue`
- `frontend/user/src/components/collaboration/CollaborationErrorState.vue`
- `frontend/user/tests/collaboration-hub-student.spec.js`

修改：

- `frontend/user/src/components/workspace/WorkspaceShell.vue`
- `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- `frontend/user/src/components/workspace/WorkspaceMobileNav.vue`

实现顺序：

1. 先列表、空状态、加载和错误。
2. 再详情内部前进/返回。
3. 再发起协调表单。
4. 再接受、婉拒、撤回。
5. 再接入现有任务提交与审核入口。
6. 最后接入跨路由状态保持和焦点管理。

视觉约束：

- 448px 桌面宽度。
- 16px 容器圆角。
- `--ds-shadow-soft`。
- 普通任务开放列表。
- 当前待处理项才用浅橙强调。
- 36px 紧凑按钮。
- 四格品牌标识不使用渐变。

移动端：

- 同一组件切换为底部抽屉。
- 不叠加第二层弹窗。
- 关闭后焦点返回协作入口。
- 390px 下无横向滚动。

### 任务 14：接入学生任务提交、审核和完整协作台

修改：

- `frontend/user/src/views/ProjectTeam.vue`
- `frontend/user/src/components/collaboration/CollaborationDetail.vue`
- `frontend/user/src/components/collaboration/CollaborationItemRow.vue`
- `frontend/user/tests/collaboration-pages-design.spec.js`
- `frontend/user/tests/collaboration-hub-student.spec.js`

实现：

1. 项目任务列表显示 `sourceType`。
2. 同学协调任务显示协调发起人和审核人。
3. 浮窗复杂详情跳转：

```text
/project-team/details/task-{taskId}?teamId={teamId}
```

4. 学生提交继续使用：

```text
POST /api/project-teams/tasks/{taskId}/submissions
```

5. 发起人审核继续使用：

```text
POST /api/project-teams/submissions/{submissionId}/review
```

6. 提交失败保留输入、文件选择结果和说明。
7. 状态冲突刷新当前条目而不是关闭浮窗。

## 7. 阶段三：教师端协作工作台

### 任务 15：增加教师端实时依赖与通知客户端

修改：

- `frontend/teacher/package.json`
- `frontend/teacher/package-lock.json`

新增：

- `frontend/teacher/src/utils/websocket.js`
- `frontend/teacher/src/services/notificationClient.js`
- `frontend/teacher/tests/notification-client-contract.test.mjs`

依赖：

- `@stomp/stompjs`
- `sockjs-client`

实现：

- 使用与学生端相同的 `/ws` 和 `/user/queue/notifications`。
- 保持单连接、多 callback 分发。
- 页面 focus 和重连时回补 summary。
- 读取教师端 token 工具，不复制学生端本地存储键。

安装与验证：

```bash
cd frontend/teacher
npm install @stomp/stompjs sockjs-client
node --test tests/notification-client-contract.test.mjs
npm run build
```

### 任务 16：增加教师协作客户端与 store

新增：

- `frontend/teacher/src/services/collaborationClient.js`
- `frontend/teacher/src/stores/collaboration.js`
- `frontend/teacher/tests/collaboration-store-contract.test.mjs`

修改：

- `frontend/teacher/src/api/index.js`

实现：

1. 聚合列表和 summary 使用 `/api/collaboration/*`。
2. 发布正式任务复用 `createTeamTask`。
3. 审核复用 `reviewSubmission`。
4. 团队列表复用 `fetchMyTeams` 和教师上下文 store。
5. 当前 team 为 `all` 时，聚合接口使用教师管理范围。
6. 切换教师顶部团队时，浮窗团队范围同步更新。
7. 浮窗内部切换团队时，不意外改变当前页面业务上下文；只有用户明确选择“同步当前团队”时才更新全局上下文。

### 任务 17：实现教师协作入口与浮窗

新增：

- `frontend/teacher/src/components/collaboration/CollaborationBrandMark.vue`
- `frontend/teacher/src/components/collaboration/TeacherCollaborationEntry.vue`
- `frontend/teacher/src/components/collaboration/TeacherCollaborationHub.vue`
- `frontend/teacher/src/components/collaboration/TeacherCollaborationList.vue`
- `frontend/teacher/src/components/collaboration/TeacherTaskForm.vue`
- `frontend/teacher/src/components/collaboration/TeacherReviewDetail.vue`
- `frontend/teacher/tests/collaboration-hub-contract.test.mjs`

修改：

- `frontend/teacher/src/components/TeacherShell.vue`
- `frontend/teacher/src/styles/teacher.css`

实现：

1. 入口放在 `.teacher-rail__nav` 之后、rail 底部。
2. 不加入 `TEACHER_RAIL` 普通路由数组。
3. 待审核徽标只统计需要教师操作的成果。
4. 浮窗提供团队切换、待审核、进行中、已发布、已完成。
5. “发布任务”复用现有任务表单字段和 API。
6. “开始审核”复用现有 submission review API。
7. 桌面视觉与学生端一致，允许教师列表行更紧凑。
8. 移动端教师壳层下使用同样的底部抽屉规则。

验证：

```bash
cd frontend/teacher
node --test \
  tests/collaboration-store-contract.test.mjs \
  tests/collaboration-hub-contract.test.mjs
npm run build
```

## 8. 端到端测试与回归

### 任务 18：增加学生协调 E2E

新增：

- `frontend/user/tests/collaboration-peer-flow.spec.js`

覆盖：

1. 徽标数量。
2. 发起协调。
3. 接收人接受。
4. 重复点击不重复建任务。
5. 提交成果。
6. 发起人退回。
7. 再次提交。
8. 发起人通过。
9. 资源中心出现最终成果。
10. 路由切换后浮窗和草稿保持。
11. WebSocket 事件刷新列表但不覆盖草稿。
12. 390px 底部抽屉完整可用。

### 任务 19：增加教师协作 E2E

新增：

- `frontend/user/tests/collaboration-teacher-flow.spec.js`

运行时使用：

```bash
OREP_E2E_BASE_URL=http://localhost:5175
```

覆盖：

1. 教师入口位置和视觉。
2. 团队范围只出现管理团队。
3. 多负责人发布。
4. 待审核数量。
5. 通过和退回。
6. 非管理团队接口失败时不泄露数据。
7. 教师页面切换后浮窗保持。

### 任务 20：完整回归命令

后端：

```bash
cd backend
mvn -Dtest=\
CollaborationMigrationContractTest,\
CollaborationServiceTest,\
CollaborationControllerTest,\
NotificationServiceTest,\
NotificationControllerTest,\
ProjectTeamServiceReviewTest,\
ProjectTeamServiceMembershipTest \
test
mvn test
```

学生端：

```bash
cd frontend/user
node --test \
  tests/resource-center-navigation-contract.test.mjs \
  tests/websocket-multisubscriber-contract.test.mjs \
  tests/collaboration-store-contract.test.mjs
npx playwright test \
  tests/workspace-sidebar-navigation.spec.js \
  tests/workspace-route-shell-stability.spec.js \
  tests/collaboration-pages-design.spec.js \
  tests/notification-center.spec.js \
  tests/collaboration-entry-shell.spec.js \
  tests/collaboration-hub-student.spec.js \
  tests/collaboration-peer-flow.spec.js
npm run build
```

教师端：

```bash
cd frontend/teacher
node --test tests/*.test.mjs
npm run build
```

视觉验证：

- 学生端：1545×1071、1280×900、1024×768、390×844。
- 教师端：1545×1071、1180×800、720×900。
- 验证无横向滚动、无遮挡、焦点顺序正确。

## 9. 灰度与部署计划

### 9.1 配置

后端：

```text
OREP_COLLABORATION_ENABLED=false
```

学生端：

```text
VITE_COLLABORATION_ENABLED=false
```

教师端：

```text
VITE_COLLABORATION_ENABLED=false
```

阶段一资源中心迁移不依赖协作开关。

### 9.2 上线顺序

1. 数据库备份。
2. 执行 V107。
3. 部署后端，开关关闭。
4. 验证旧任务、旧提交、旧通知。
5. 部署学生端，验证资源中心与旧路由。
6. 部署教师端，验证现有任务发布与审核。
7. 内部租户开启后端和前端开关。
8. 执行两条端到端流程。
9. 查看错误率、冲突数、通知失败和资源同步失败。
10. 逐步扩大租户范围。

### 9.3 回滚

- 前端：关闭 `VITE_COLLABORATION_ENABLED`，入口回退到 `/project-team`。
- 后端：关闭 `OREP_COLLABORATION_ENABLED`。
- 已接受请求生成的正式任务继续通过 `/project-team` 处理。
- 不删除 V107 表和字段。
- `/resource-center` 可继续保留；必要时恢复旧导航链接。

## 10. 完成标准

只有同时满足以下条件才能宣布完成：

- 设计规格中的全部验收项有对应测试或人工验证记录。
- 新增和既有后端专项测试通过。
- 两个前端生产构建通过。
- 学生和教师 E2E 通过。
- 旧文件与任务地址无 404。
- 学生不能跨团队或跨租户协调。
- 普通学生不能审核非本人发起的协调任务。
- 同一请求不会生成重复任务。
- 顶部通知与协作浮窗可以同时接收 WebSocket 消息。
- 新协作成果只在审核通过后同步资源中心。
- 既有训练任务同步语义没有改变。
- 桌面和移动端视觉符合平台 token。
- 灰度监控无权限泄漏和高频错误。

## 11. 执行检查点

每个检查点完成后再进入下一项：

1. 资源中心路由与导航通过。
2. V107 和通知泛化测试通过。
3. 协调服务与权限测试通过。
4. 学生端完整流程通过。
5. 教师端完整流程通过。
6. 全量回归通过。
7. 本地生产构建验证通过。
8. 线上灰度验证通过。

任何检查点失败时，只修复当前阶段，不提前部署后续阶段。
