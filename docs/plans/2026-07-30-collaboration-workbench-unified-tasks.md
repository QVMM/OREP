# 协作品牌图标与统一任务工作台实施计划

日期：2026-07-30  
依据：`docs/superpowers/specs/2026-07-30-collaboration-workbench-unified-tasks-design.md`

## 目标

在不改变协作请求和项目任务写模型的前提下，把协作读取接口升级为统一工作项投影，并让用户端、教师端共用新的连接节点图标、四分类和任务表达。

## 实施顺序

### 1. 后端读取模型测试

新增 `CollaborationWorkItemServiceTest`，覆盖：

- 学生只能读取自己负责的任务和自己参与的请求；
- 今日训练、老师任务、团队任务、学生协作来源归一；
- 未解锁训练任务对学生不可见；
- 已接受请求与 `linked_task_id` 任务去重；
- 待审核提交为教师任务增加 `REVIEW` 主操作；
- `ACTION_REQUIRED`、`IN_PROGRESS`、`CREATED_BY_ME`、`ALL` 分类与摘要一致；
- `teamId` 不能扩大服务端权限范围。

更新 `CollaborationControllerTest`，确保两个读取接口委托给新的工作项服务，写接口仍委托给原协作服务。

### 2. 后端统一工作项服务

新增：

- `backend/src/main/java/com/orep/backend/service/CollaborationWorkItemService.java`

修改：

- `backend/src/main/java/com/orep/backend/controller/CollaborationController.java`
- `backend/src/main/java/com/orep/backend/service/CollaborationService.java`

实现内容：

- 一次读取授权团队、任务、训练日关联、最新提交和协作请求；
- 构造统一字段、目标路由、主操作；
- 请求/任务去重；
- 四分类过滤、排序和分页；
- 摘要复用同一工作项集合；
- 保留请求详情及接受、拒绝、撤回写流程。

### 3. 用户端图标与工作台

修改：

- `frontend/user/src/components/collaboration/CollaborationBrandMark.vue`
- `frontend/user/src/components/collaboration/CollaborationEntry.vue`
- `frontend/user/src/components/collaboration/CollaborationHub.vue`
- `frontend/user/src/components/collaboration/CollaborationItemRow.vue`
- `frontend/user/src/stores/collaboration.js`
- `frontend/user/src/services/collaborationClient.js`

实现内容：

- 使用确认后的连接节点 SVG、18px 加粗描边和品牌渐变；
- 统一四分类；
- 显示来源、状态、团队、发布人和截止时间；
- 请求保留接受、拒绝、撤回；
- 任务按 `primaryAction` 打开训练任务、项目任务或提交/审核入口；
- 角标与 `actionRequired` 一致；
- 保留焦点恢复、实时刷新和移动端浮层。

### 4. 教师端统一

修改：

- `frontend/teacher/src/components/collaboration/CollaborationBrandMark.vue`
- `frontend/teacher/src/components/collaboration/TeacherCollaborationHub.vue`
- `frontend/teacher/src/stores/collaboration.js`
- `frontend/teacher/src/services/collaborationClient.js`

实现内容：

- 与用户端使用相同图标；
- 使用统一摘要和工作项接口；
- 四分类替换现有教师专属分类；
- 保留团队范围、发布任务和审核详情；
- `REVIEW` 工作项进入现有 `TeacherReviewDetail`。

### 5. 自动化验证

更新或新增：

- 后端服务和控制器测试；
- 用户端协作 store/组件契约测试；
- 用户端 Playwright 测试，覆盖请求、训练/老师任务、跳转与移动端；
- 教师端协作 store/组件契约测试。

执行：

```text
cd backend && mvn -Dtest=CollaborationServiceTest,CollaborationWorkItemServiceTest,CollaborationControllerTest test
cd frontend/user && node --test tests/collaboration-*-contract.test.mjs
cd frontend/user && npx playwright test tests/collaboration-hub-student.spec.js
cd frontend/user && npm run build
cd frontend/teacher && node --test tests/collaboration-*-contract.test.mjs
cd frontend/teacher && npm run build
```

最后在本地登录态页面检查侧栏小尺寸图标、角标、四分类、任务行和目标跳转。
