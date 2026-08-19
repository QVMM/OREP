# Course Learning Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete course learning module with database tables, Spring Boot APIs, and a SpaceX-style Vue UI.

**Architecture:** Add course catalog, chapter, lesson, attachment, and per-user progress tables. The backend exposes authenticated `/api/courses` endpoints and returns view objects that merge course metadata with the current user's progress. The frontend replaces the placeholder course page with an API-driven course list/detail experience.

**Tech Stack:** Spring Boot 3, Java 21, MyBatis-Plus, MySQL, Vue 3, Element Plus, Vite.

---

### Task 1: Backend Schema and Course API

**Files:**
- Create: `backend/src/test/java/com/orep/backend/service/CourseServiceTest.java`
- Create: `backend/src/main/resources/sql/create_course_learning_tables.sql`
- Create: `backend/src/main/java/com/orep/backend/entity/Course.java`
- Create: `backend/src/main/java/com/orep/backend/entity/CourseChapter.java`
- Create: `backend/src/main/java/com/orep/backend/entity/CourseLesson.java`
- Create: `backend/src/main/java/com/orep/backend/entity/CourseAttachment.java`
- Create: `backend/src/main/java/com/orep/backend/entity/CourseLearningProgress.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/CourseMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/CourseChapterMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/CourseLessonMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/CourseAttachmentMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/CourseLearningProgressMapper.java`
- Create: `backend/src/main/java/com/orep/backend/dto/CourseVO.java`
- Create: `backend/src/main/java/com/orep/backend/dto/CourseDetailVO.java`
- Create: `backend/src/main/java/com/orep/backend/service/CourseService.java`
- Create: `backend/src/main/java/com/orep/backend/controller/CourseController.java`

- [ ] Write a failing service test for filtering courses with progress.
- [ ] Add SQL tables and seed data for the three reference courses.
- [ ] Add entities, mappers, DTOs, service, and controller.
- [ ] Run `mvn test -Dtest=CourseServiceTest` and `mvn compile`.

### Task 2: Frontend Course Learning Page

**Files:**
- Modify: `frontend/user/src/views/CourseLearning.vue`

- [ ] Replace the static placeholder with API-backed state.
- [ ] Render filter tabs, category selector, course cards, detail hero, course catalog, and attachments.
- [ ] Persist progress when users continue or complete a lesson.
- [ ] Keep the visual language consistent with the OREP dark mission-control style.
- [ ] Run `npm run build`.

