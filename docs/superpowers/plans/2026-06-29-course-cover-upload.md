# Course Cover Upload Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 管理端课程管理可上传课程卡片封面图，用户端课程学习页课程卡片显示封面。

**Architecture:** 复用课程表既有 `coverUrl` 字段。后端新增一个管理端封面上传接口保存文件并更新课程，前端管理端表单调用该接口，用户端课程卡片继续从课程列表接口读取 `coverUrl` 渲染。

**Tech Stack:** Spring Boot、MyBatis Plus、JUnit/MockMvc、Vue 3、Element Plus、Vite。

---

## Files

- Modify: `backend/src/main/java/com/orep/backend/service/CourseService.java`，增加封面更新方法。
- Modify: `backend/src/main/java/com/orep/backend/controller/AdminCourseController.java`，增加封面上传接口和图片校验。
- Modify: `backend/src/test/java/com/orep/backend/controller/CourseControllerTest.java` 或新增管理端上传测试，覆盖成功/非法格式。
- Modify: `frontend/admin/src/views/CourseManagement.vue`，课程编辑弹窗加入封面预览、上传、URL 输入。
- Modify: `frontend/user/src/views/CourseLearning.vue`，确认卡片封面有图显示图片、无图保留渐变。

### Task 1: Backend Cover Persistence

- [ ] 在 `CourseService.java` 增加 `updateCourseCover(Long id, String coverUrl, Long userId, String role)`，通过 `courseMapper.selectById` 找课程，使用 `canAccessAdminCourse` 校验，设置 `coverUrl` 后更新并返回课程。
- [ ] 确认 `applyCourseRequest` 已经保存 `coverUrl`，无需重复改数据模型。

### Task 2: Backend Upload API

- [ ] 在 `AdminCourseController.java` 增加 `POST /{id}/cover`。
- [ ] 校验文件非空、扩展名为 `jpg/jpeg/png/webp`、大小不超过 5MB。
- [ ] 按 `course-covers/{courseId}/yyyy/MM/dd` 保存文件，路径必须保持在 `uploadDir` 下。
- [ ] 调用 `courseService.updateCourseCover` 写入 `/uploads/{relativePath}`。
- [ ] 返回 `courseId`、`coverUrl`。

### Task 3: Admin UI Upload

- [ ] 在课程编辑弹窗增加 `课程封面` 表单项。
- [ ] 添加预览块，`courseForm.coverUrl` 有值时显示图片，没有值时显示占位说明。
- [ ] 添加 `el-upload`，请求 `/api/admin/courses/{id}/cover`，只在已有课程 ID 时启用；新建课程先保存后再上传。
- [ ] 添加 `beforeCoverUpload`、`handleCoverSuccess`、`handleCoverError`。
- [ ] 上传成功后更新 `courseForm.coverUrl`，刷新课程列表和当前详情。

### Task 4: User Course Card Rendering

- [ ] 保留 `courseCoverStyle(course)` 对 `coverUrl` 的支持。
- [ ] 调整 `.course-card__cover` 样式，图片居中裁切，编号在图片上仍可读。
- [ ] 无图片时不改变现有渐变封面行为。

### Task 5: Verification

- [ ] 运行后端课程相关测试：`mvn test -Dtest=CourseControllerTest,CourseServiceTest`。
- [ ] 运行管理端构建：`npm run build` in `frontend/admin`。
- [ ] 运行用户端构建：`npm run build` in `frontend/user`。
- [ ] 自查改动，确认没有修改构建产物或无关文件。
