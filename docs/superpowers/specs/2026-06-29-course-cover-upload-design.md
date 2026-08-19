# Course Cover Upload Design

## Goal

在管理端课程管理中支持上传课程首页卡片封面图，并让用户端课程学习页课程卡片显示该图片。

## Scope

- 复用现有 `course.cover_url` / `Course.coverUrl` 字段，不新增数据表。
- 管理端课程编辑弹窗增加封面上传与预览。
- 后端新增课程封面上传接口，保存图片后写回课程 `coverUrl`。
- 用户端课程卡片按 `coverUrl` 展示图片；无图片时保持现有渐变样式。

## Backend Design

- 在 `AdminCourseController` 新增 `POST /api/admin/courses/{id}/cover`。
- 仅允许 `jpg`、`jpeg`、`png`、`webp`，最大 5MB。
- 文件保存到 `file.upload-dir` 下的 `course-covers/{courseId}/yyyy/MM/dd/{uuid}.{ext}`。
- 返回并持久化 `/uploads/...` URL。
- 在 `CourseService` 增加 `updateCourseCover`，复用 `canAccessAdminCourse` 权限逻辑。

## Frontend Design

- 管理端 `CourseManagement.vue` 的课程表单增加封面区：当前图片预览、上传按钮、手动 URL 输入。
- 上传成功后更新 `courseForm.coverUrl`，并刷新课程列表/当前详情。
- 用户端 `CourseLearning.vue` 已有 `courseCoverStyle(course)`，保留并加强有图/无图样式分层。

## Validation

- 后端上传合法图片返回 `coverUrl` 并更新课程。
- 非图片扩展名或超过 5MB 返回 400。
- 前端构建通过。
- 用户端课程卡片有图显示图片，无图保持现有视觉。
