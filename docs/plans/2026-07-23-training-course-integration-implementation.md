# 课程学习与训练任务融合实施计划

日期：2026-07-23  
依据：[课程学习与训练任务融合设计](../superpowers/specs/2026-07-23-training-course-integration-design.md)  
执行状态：待实施

## 总体策略

按依赖顺序分六个阶段实施：

1. 数据表与资源存储
2. 教师端编排接口与界面
3. 学生端读取、学习进度与界面
4. 独立课程入口收口
5. 历史入口与测试更新
6. 全链路回归与数据兼容验证

每层完成后先通过对应测试，再进入下一层。历史课程表和学习记录全程只读保留，不做删除或批量迁移。

## 阶段 1：训练日学习资源数据层

### 任务 1.1：新增数据库迁移

新增文件：

- `backend/src/main/resources/sql/create_training_day_learning_resources.sql`

创建：

- `training_day_learning_resource`
- `training_learning_progress`

约束与索引：

- 资源表关联 `training_day.id`
- 进度表关联资源和用户
- `user_id + learning_resource_id` 唯一
- `training_day_id + status + sort_order` 复合索引
- 训练日和学习资源使用限制删除；业务层只归档资源，不物理删除已有记录
- 用户删除时级联清理该用户的学习进度，不影响资源记录

迁移要求：

- 使用 `CREATE TABLE IF NOT EXISTS`
- 枚举值通过 `VARCHAR` 与服务端白名单控制
- 不修改原 `course*` 表
- 在部署说明中明确先执行迁移再启动新版本

### 任务 1.2：新增资源服务

新增文件：

- `backend/src/main/java/com/orep/backend/service/TrainingDayLearningResourceService.java`
- `backend/src/test/java/com/orep/backend/service/TrainingDayLearningResourceServiceTest.java`

职责：

- 校验教师对训练日的访问权限
- 创建外部链接资源
- 上传视频和文档
- 更新标题、说明、必学状态和预计时长
- 调整排序
- 归档资源
- 发布时激活资源
- 查询教师端资源、学生端有效资源和个人进度

文件策略：

- 存储目录：`uploads/training/learning/{dayId}/`
- 视频与文档分目录存储
- 随机存储文件名，保留展示文件名
- 视频限制为 500MB，文档限制为 50MB，允许类型集中定义
- 校验扩展名、MIME 类型、文件头和标准化路径
- 外部链接只允许 HTTPS

测试：

- 无权限教师被拒绝
- 非法类型、超限文件和伪造 MIME 被拒绝
- 非 HTTPS 链接被拒绝
- 排序只影响当前训练日
- 归档资源不再出现在学生查询
- 已有进度的资源归档后进度仍保留

验证命令：

```bash
cd backend
mvn -Dtest=TrainingDayLearningResourceServiceTest test
```

## 阶段 2：教师端接口与每日编排

### 任务 2.1：扩展教师端接口

修改文件：

- `backend/src/main/java/com/orep/backend/controller/TeacherPortalController.java`
- `backend/src/main/java/com/orep/backend/service/TeacherPortalService.java`

新增接口：

- `POST /api/teacher/portal/camp/days/{dayId}/learning-resources/files`
- `POST /api/teacher/portal/camp/days/{dayId}/learning-resources/links`
- `PATCH /api/teacher/portal/camp/days/{dayId}/learning-resources/{resourceId}`
- `DELETE /api/teacher/portal/camp/days/{dayId}/learning-resources/{resourceId}`，服务端执行归档而非物理删除
- `PATCH /api/teacher/portal/camp/days/{dayId}/learning-resources/order`

调整：

- `GET /api/teacher/portal/camp` 的每个训练日返回 `learningResources`
- 发布训练日时校验学习资源并激活 `PENDING` 资源
- 上传失败资源不能进入可发布列表
- 已发布训练日再次发布时保留学生进度

新增测试：

- `backend/src/test/java/com/orep/backend/controller/TeacherPortalLearningResourceControllerTest.java`

覆盖：

- 认证上下文透传
- 文件与链接请求结构
- 更新、排序、归档
- 发布时资源状态切换

### 任务 2.2：增加教师端 API 封装

修改文件：

- `frontend/teacher/src/api/index.js`

新增函数：

- `uploadTeacherLearningResource`
- `createTeacherLearningLink`
- `updateTeacherLearningResource`
- `deleteTeacherLearningResource`
- `reorderTeacherLearningResources`

约定：

- 文件上传使用 `FormData`
- 链接和元数据使用 JSON
- 错误消息使用现有响应解包逻辑

### 任务 2.3：实现“今日学习”编辑器

新增文件：

- `frontend/teacher/src/components/training/TrainingLearningResourcesEditor.vue`
- `frontend/teacher/src/components/training/TrainingLearningResourceDialog.vue`

修改文件：

- `frontend/teacher/src/views/camp/CampPlanView.vue`

界面顺序：

1. 任务标题
2. 训练说明
3. 今日学习
4. 详细任务说明
5. 截止时间
6. 任务附件
7. 交付要求

编辑器能力：

- 显示资源数量、必学数量和预计总时长
- 添加视频、文档和外部链接
- 设置标题、说明、必学/选学和预计时长
- 拖拽或上移/下移排序
- 预览、替换、删除
- 上传中、失败、待发布、已发布状态
- 资源较多时折叠为摘要

发布校验：

- 标题不能为空
- 链接必须有效且为 HTTPS
- 文件必须上传成功
- 失败项在区块内定位并显示原因

### 任务 2.4：收口教师端独立课程入口

修改文件：

- `frontend/teacher/src/config/nav.js`
- `frontend/teacher/src/router/index.js`
- `frontend/teacher/src/views/camp/CampPlanView.vue`

处理：

- 从集训营二级导航移除“课程”
- `/camp/courses` 重定向至 `/camp/plan`
- 移除“关联课程”按钮
- 保留 `CampCoursesView.vue` 源码，不删除历史能力

教师端验证：

```bash
cd frontend/teacher
npm run build
```

浏览器验收：

- 日任务编辑器能够添加三种资源
- 切换训练日不会串数据
- 草稿资源学生不可见
- 发布后资源状态正确
- 窄屏表单没有横向溢出

## 阶段 3：学生端接口与学习进度

### 任务 3.1：扩展训练计划与详情数据

修改文件：

- `backend/src/main/java/com/orep/backend/service/StudentTrainingService.java`
- `backend/src/main/java/com/orep/backend/controller/StudentTrainingController.java`
- `backend/src/test/java/com/orep/backend/controller/StudentTrainingControllerTest.java`

训练计划每日摘要增加：

- `learningResourceCount`
- `requiredLearningCount`
- `estimatedLearningMinutes`
- `completedLearningCount`

训练日详情增加：

- `learningResources`
- 每条资源的 `progressPercent`
- `learnedSeconds`
- `learningStatus`
- `completedAt`

查询要求：

- 只返回 `ACTIVE` 资源
- 只返回当前学生可访问训练营的资源
- 一次批量查询全部训练日摘要，避免逐日 N+1
- 详情查询一次加载资源与当前用户进度

### 任务 3.2：新增学生进度接口

新增或修改文件：

- `backend/src/main/java/com/orep/backend/controller/StudentTrainingController.java`
- `backend/src/main/java/com/orep/backend/service/TrainingLearningProgressService.java`
- `backend/src/test/java/com/orep/backend/service/TrainingLearningProgressServiceTest.java`

新增接口：

- `PATCH /api/training-learning-resources/{resourceId}/progress`
- `POST /api/training-learning-resources/{resourceId}/complete`

规则：

- 视频进度百分比限制在 0–100
- 视频达到 90% 自动完成
- 文档和链接允许手动完成
- 学生只能更新自己可访问训练日的资源
- 并发更新使用向前推进原则，不允许旧进度覆盖新进度
- 资源归档后禁止新增进度，但保留原记录

测试：

- 视频阈值
- 手动完成类型限制
- 越权访问
- 并发进度不倒退
- 归档资源处理

## 阶段 4：学生端三步流程 UI

### 任务 4.1：扩展前端 API

修改文件：

- `frontend/user/src/modules/training/api.js`

新增：

- `updateTrainingLearningProgress`
- `completeTrainingLearningResource`

### 任务 4.2：实现今日学习区块

新增文件：

- `frontend/user/src/modules/training/components/TrainingLearningSection.vue`
- `frontend/user/src/modules/training/components/TrainingLearningItem.vue`

修改文件：

- `frontend/user/src/modules/training/TrainingDayView.vue`

结构：

- 今日学习
- 今日任务
- 成果提交

交互：

- 有资源时默认展开
- 全部必学完成后自动折叠
- 没有资源时完全不渲染
- 视频内嵌播放并节流同步进度
- 文档调用现有 `FilePreview`
- 外部链接新窗口打开
- 文件和链接支持手动标记已学
- 同步失败显示轻提示并保留本地状态
- 未完成必学内容在提交区显示非阻断提醒

可访问性：

- 折叠区有 `aria-expanded`
- 进度和状态不只依赖颜色
- 播放与完成操作可用键盘触发

### 任务 4.3：增加训练列表摘要

修改文件：

- `frontend/user/src/modules/training/TrainingPlan.vue`

展示规则：

- 有学习内容时显示“X 项学习 · Y 项任务 · 预计 Z 分钟”
- 无学习内容时不显示学习摘要
- 学习资源不计入任务状态筛选数量
- 保持每日卡片高度稳定

### 任务 4.4：新增学生端端到端测试

新增文件：

- `frontend/user/tests/training-learning-integration.spec.js`

更新文件：

- `frontend/user/tests/training-task-list.spec.js`
- `frontend/user/tests/training-copy.spec.js`

场景：

- 列表展示学习摘要
- 详情显示三步流程
- 无学习资源时不显示空区块
- 视频进度达到阈值后完成
- 文件与链接手动完成
- 必学未完成不阻断提交
- 全部必学完成后区块折叠
- 窄屏没有水平滚动

## 阶段 5：移除学生端独立课程入口

### 任务 5.1：导航与路由收口

修改文件：

- `frontend/user/src/components/workspace/WorkspaceModuleNav.vue`
- `frontend/user/src/components/workspace/WorkspaceTopbar.vue`
- `frontend/user/src/components/workspace/WorkspaceShell.vue`
- `frontend/user/src/composables/apple/useOrepNavigation.js`
- `frontend/user/src/router/index.js`
- `frontend/user/src/components/layout/AppHeader.vue`
- `frontend/user/src/components/dashboard/QuickEntry.vue`
- `frontend/user/src/views/Dashboard.vue`

处理：

- 移除“课程学习”导航、搜索和快捷入口
- `/course-learning/:pathMatch(.*)*` 统一重定向 `/training/today`
- 首页练习路径直接进入训练任务
- 保留 `CourseLearning.vue` 和 `CourseLessonPlayer.vue` 源码
- 不修改个人中心历史学习时长统计

### 任务 5.2：更新旧课程测试

更新文件：

- `frontend/user/tests/course-learning-suggestions.spec.js`

将旧课程 UI 断言替换为：

- 课程基础地址跳转训练任务
- 课程详情地址跳转训练任务
- 课时播放地址跳转训练任务
- 训练营侧栏不显示课程学习

## 阶段 6：全链路验证

### 后端

```bash
cd backend
mvn test
```

重点确认：

- 新迁移可重复执行
- 资源权限隔离
- 进度并发更新
- 原课程测试仍通过
- 原训练任务与提交接口未回归

### 教师端

```bash
cd frontend/teacher
npm run build
```

浏览器检查：

- 训练日切换
- 三种资源添加
- 上传失败和重试
- 排序、替换和删除
- 草稿与发布
- 旧课程路由跳转
- 1280px 与 390px 布局

### 学生端

```bash
cd frontend/user
npm run build
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/training-task-list.spec.js \
  tests/training-copy.spec.js \
  tests/training-learning-integration.spec.js \
  tests/course-learning-suggestions.spec.js
```

浏览器检查：

- 每日列表摘要
- 三步详情结构
- 视频、文件和链接学习
- 未完成提示与成果提交
- 完成后折叠
- 历史课程地址跳转
- 无学习内容兼容
- 窄屏无横向滚动

## 实施风险与控制

### 大文件上传

风险：视频上传时间长、失败率高。  
控制：本阶段先沿用单次上传并明确大小上限、进度和重试；不把分片上传作为首版阻塞项。

### 进度写入频率

风险：视频高频上报增加数据库压力。  
控制：前端每 10–15 秒或暂停、离开页面时同步；服务端只接受向前进度。

### 已发布资源更新

风险：资源替换后学生误以为已学内容没有变化。  
控制：保留历史完成记录，同时在资源行显示“内容已更新”，允许重新学习。

### 历史课程数据

风险：关闭入口后误删历史统计。  
控制：不修改原课程表和个人中心聚合逻辑；只收口导航与路由。

### 页面信息密度

风险：学习、任务和提交全部同页导致过长。  
控制：学习区块可折叠、资源使用紧凑行、已完成自动收起、窄屏保持单列。

## 完成定义

只有同时满足以下条件才算完成：

1. 教师可按训练日添加、排序并发布三种学习内容。
2. 学生可在任务详情完成学习、任务和提交，不跳出训练流程。
3. 学习进度可追踪，必学未完成只提示不阻断。
4. 独立课程入口与旧路由已收口。
5. 历史课程数据和学习时长未被删除或覆盖。
6. 后端测试、两端构建和目标端到端测试全部通过。
