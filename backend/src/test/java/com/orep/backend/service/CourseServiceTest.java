package com.orep.backend.service;

import com.orep.backend.dto.CourseVO;
import com.orep.backend.entity.Course;
import com.orep.backend.entity.CourseAttachment;
import com.orep.backend.entity.CourseChapter;
import com.orep.backend.entity.CourseLearningProgress;
import com.orep.backend.entity.CourseLesson;
import com.orep.backend.mapper.CourseChapterMapper;
import com.orep.backend.mapper.CourseAttachmentMapper;
import com.orep.backend.mapper.CourseLearningProgressMapper;
import com.orep.backend.mapper.CourseLessonMapper;
import com.orep.backend.mapper.CourseMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.time.LocalDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.Mockito.atLeastOnce;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class CourseServiceTest {

    @Test
    void ensureSchemaCreatesCourseLearningTablesAndVideoColumnsForFreshDatabase() {
        org.springframework.jdbc.core.JdbcTemplate jdbc = mock(org.springframework.jdbc.core.JdbcTemplate.class);
        CourseService service = new CourseService(null, null, null, null, null, jdbc);

        service.ensureSchema();

        verify(jdbc).execute(contains("CREATE TABLE IF NOT EXISTS course "));
        verify(jdbc).execute(contains("CREATE TABLE IF NOT EXISTS course_chapter"));
        verify(jdbc).execute(contains("CREATE TABLE IF NOT EXISTS course_lesson"));
        verify(jdbc).execute(contains("CREATE TABLE IF NOT EXISTS course_attachment"));
        verify(jdbc).execute(contains("CREATE TABLE IF NOT EXISTS course_learning_progress"));
        verify(jdbc).execute(contains("ADD COLUMN video_file_path"));
        verify(jdbc).execute(contains("ADD COLUMN video_mime_type"));
        verify(jdbc).execute(contains("ADD COLUMN video_size_bytes"));
        verify(jdbc).execute(contains("SET resource_url = CONCAT('/api/courses/lessons/', id, '/stream')"));
    }

    @Test
    void listCoursesMergesCurrentUserProgressAndFiltersCompletedCourses() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseLearningProgressMapper progressMapper = mock(CourseLearningProgressMapper.class);
        CourseService service = new CourseService(courseMapper, null, null, null, progressMapper, null);

        Course required = course(1L, "人工智能进阶课程", "required");
        Course elective = course(2L, "Python编程基础", "elective");

        CourseLearningProgress finished = new CourseLearningProgress();
        finished.setCourseId(1L);
        finished.setUserId(8L);
        finished.setProgressPercent(100);
        finished.setStatus("completed");

        CourseLearningProgress untouched = new CourseLearningProgress();
        untouched.setCourseId(2L);
        untouched.setUserId(8L);
        untouched.setProgressPercent(0);
        untouched.setStatus("not_started");

        when(courseMapper.selectList(any())).thenReturn(List.of(required, elective));
        when(progressMapper.selectList(any())).thenReturn(List.of(finished, untouched));

        List<CourseVO> courses = service.listCourses(8L, "completed", null);

        assertThat(courses).hasSize(1);
        assertThat(courses.get(0).getId()).isEqualTo(1L);
        assertThat(courses.get(0).getProgressPercent()).isEqualTo(100);
        assertThat(courses.get(0).getLearningStatus()).isEqualTo("completed");
    }

    @Test
    void attachLessonVideoStoresPlayableVideoMetadata() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseLessonMapper lessonMapper = mock(CourseLessonMapper.class);
        CourseService service = new CourseService(courseMapper, null, lessonMapper, null, null, null);
        CourseLesson lesson = new CourseLesson();
        lesson.setId(9L);
        lesson.setCourseId(3L);
        lesson.setTitle("工程化视频课");
        when(lessonMapper.selectById(9L)).thenReturn(lesson);
        when(courseMapper.selectById(3L)).thenReturn(course(3L, "工程化视频课", "required"));

        CourseLesson updated = service.attachLessonVideo(9L, "course-videos/3/demo.mp4", "video/mp4", 2048L, 95, 8L, "ADMIN");

        assertThat(updated.getResourceUrl()).isEqualTo("/api/courses/lessons/9/stream");
        assertThat(updated.getVideoFilePath()).isEqualTo("course-videos/3/demo.mp4");
        assertThat(updated.getVideoMimeType()).isEqualTo("video/mp4");
        assertThat(updated.getVideoSizeBytes()).isEqualTo(2048L);
        assertThat(updated.getDurationSeconds()).isEqualTo(95);
        verify(lessonMapper).updateById(updated);
    }

    @Test
    void createAttachmentStoresCourseAttachmentMetadata() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseAttachmentMapper attachmentMapper = mock(CourseAttachmentMapper.class);
        CourseService service = new CourseService(courseMapper, null, null, attachmentMapper, null, null);
        when(courseMapper.selectById(3L)).thenReturn(course(3L, "附件课程", "required"));

        CourseAttachment attachment = service.createAttachment(3L, "课程资料.pdf", "/api/courses/attachments/9/download", "pdf", "128 KB", 20, 8L, "ADMIN");

        assertThat(attachment.getCourseId()).isEqualTo(3L);
        assertThat(attachment.getName()).isEqualTo("课程资料.pdf");
        assertThat(attachment.getFileUrl()).isEqualTo("/api/courses/attachments/9/download");
        assertThat(attachment.getFileType()).isEqualTo("pdf");
        assertThat(attachment.getFileSize()).isEqualTo("128 KB");
        assertThat(attachment.getSortOrder()).isEqualTo(20);
        verify(attachmentMapper).insert(attachment);
    }

    @Test
    void updateCourseCoverStoresCoverUrlForAccessibleCourse() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseService service = new CourseService(courseMapper, null, null, null, null, null);
        Course course = course(3L, "封面课程", "required");
        when(courseMapper.selectById(3L)).thenReturn(course);

        Course updated = service.updateCourseCover(3L, "/uploads/course-covers/3/demo.webp", 8L, "ADMIN");

        assertThat(updated.getCoverUrl()).isEqualTo("/uploads/course-covers/3/demo.webp");
        verify(courseMapper).updateById(updated);
    }

    @Test
    void updateChapterOnlyChangesChapterFromAccessibleCourse() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseChapterMapper chapterMapper = mock(CourseChapterMapper.class);
        CourseService service = new CourseService(courseMapper, chapterMapper, null, null, null, null);
        CourseChapter chapter = new CourseChapter();
        chapter.setId(11L);
        chapter.setCourseId(3L);
        chapter.setTitle("旧章节");
        chapter.setSortOrder(10);
        when(chapterMapper.selectById(11L)).thenReturn(chapter);
        when(courseMapper.selectById(3L)).thenReturn(course(3L, "章节课程", "required"));

        com.orep.backend.dto.AdminChapterRequest request = new com.orep.backend.dto.AdminChapterRequest();
        request.setTitle("新章节");
        request.setSortOrder(20);

        CourseChapter updated = service.updateChapter(3L, 11L, request, 8L, "ADMIN");

        assertThat(updated.getTitle()).isEqualTo("新章节");
        assertThat(updated.getSortOrder()).isEqualTo(20);
        verify(chapterMapper).updateById(updated);
    }

    @Test
    void updateLessonOnlyChangesLessonFromAccessibleCourseAndChapter() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseChapterMapper chapterMapper = mock(CourseChapterMapper.class);
        CourseLessonMapper lessonMapper = mock(CourseLessonMapper.class);
        CourseService service = new CourseService(courseMapper, chapterMapper, lessonMapper, null, null, null);
        CourseChapter chapter = new CourseChapter();
        chapter.setId(12L);
        chapter.setCourseId(3L);
        CourseLesson lesson = lesson(70L, 3L, 60);
        when(courseMapper.selectById(3L)).thenReturn(course(3L, "课时课程", "required"));
        when(lessonMapper.selectById(70L)).thenReturn(lesson);
        when(chapterMapper.selectOne(any())).thenReturn(chapter);

        com.orep.backend.dto.AdminLessonRequest request = new com.orep.backend.dto.AdminLessonRequest();
        request.setChapterId(12L);
        request.setTitle("新课时");
        request.setDurationSeconds(120);
        request.setSortOrder(30);

        CourseLesson updated = service.updateLesson(3L, 70L, request, 8L, "ADMIN");

        assertThat(updated.getTitle()).isEqualTo("新课时");
        assertThat(updated.getChapterId()).isEqualTo(12L);
        assertThat(updated.getDurationSeconds()).isEqualTo(120);
        assertThat(updated.getSortOrder()).isEqualTo(30);
        verify(lessonMapper).updateById(updated);
    }

    @Test
    void deleteAttachmentRemovesOnlyAttachmentFromSameCourse() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseAttachmentMapper attachmentMapper = mock(CourseAttachmentMapper.class);
        CourseService service = new CourseService(courseMapper, null, null, attachmentMapper, null, null);
        CourseAttachment attachment = new CourseAttachment();
        attachment.setId(9L);
        attachment.setCourseId(3L);
        when(courseMapper.selectById(3L)).thenReturn(course(3L, "附件课程", "required"));
        when(attachmentMapper.selectById(9L)).thenReturn(attachment);
        when(attachmentMapper.deleteById(9L)).thenReturn(1);

        boolean deleted = service.deleteAttachment(3L, 9L, 8L, "ADMIN");

        assertThat(deleted).isTrue();
        verify(attachmentMapper).deleteById(9L);
    }

    @Test
    void saveProgressCapsUnrealisticJumpByElapsedWatchTime() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseLessonMapper lessonMapper = mock(CourseLessonMapper.class);
        CourseLearningProgressMapper progressMapper = mock(CourseLearningProgressMapper.class);
        CourseService service = new CourseService(courseMapper, null, lessonMapper, null, progressMapper, null);

        Course course = course(7L, "防刷课验证", "required");
        CourseLesson lesson = lesson(70L, 7L, 600);
        CourseLearningProgress progress = new CourseLearningProgress();
        progress.setId(4L);
        progress.setUserId(8L);
        progress.setCourseId(7L);
        progress.setLessonId(70L);
        progress.setLearnedSeconds(10);
        progress.setProgressPercent(2);
        progress.setCompletedLessons(0);
        progress.setStatus("learning");
        progress.setLastLearnedAt(LocalDateTime.now().minusSeconds(5));

        when(courseMapper.selectById(7L)).thenReturn(course);
        when(lessonMapper.selectOne(any())).thenReturn(lesson);
        when(lessonMapper.selectCount(any())).thenReturn(1L);
        when(lessonMapper.selectList(any())).thenReturn(List.of(lesson));
        when(progressMapper.selectOne(any())).thenReturn(progress);

        service.saveProgress(8L, 7L, 70L, 300);

        ArgumentCaptor<CourseLearningProgress> captor = ArgumentCaptor.forClass(CourseLearningProgress.class);
        verify(progressMapper, atLeastOnce()).updateById(captor.capture());
        assertThat(captor.getValue().getLearnedSeconds()).isLessThanOrEqualTo(25);
    }

    @Test
    void completeLessonRejectsDirectCompletionBeforeEnoughWatchTime() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseLessonMapper lessonMapper = mock(CourseLessonMapper.class);
        CourseLearningProgressMapper progressMapper = mock(CourseLearningProgressMapper.class);
        CourseService service = new CourseService(courseMapper, null, lessonMapper, null, progressMapper, null);

        CourseLesson lesson = lesson(70L, 7L, 100);
        CourseLearningProgress progress = new CourseLearningProgress();
        progress.setId(4L);
        progress.setUserId(8L);
        progress.setCourseId(7L);
        progress.setLessonId(70L);
        progress.setLearnedSeconds(20);
        progress.setProgressPercent(20);
        progress.setCompletedLessons(0);
        progress.setStatus("learning");

        when(lessonMapper.selectById(70L)).thenReturn(lesson);
        when(progressMapper.selectOne(any())).thenReturn(progress);

        assertThatThrownBy(() -> service.completeLesson(8L, 70L))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("学习时长不足");
    }

    @Test
    void publishedCourseMediaIsReadableByAnyLoggedInUser() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseService service = new CourseService(courseMapper, null, null, null, null, null);
        when(courseMapper.selectById(7L)).thenReturn(course(7L, "已发布课", "required"));

        assertThat(service.canViewCourseMedia(7L, 10L, "STUDENT")).isTrue();
        assertThat(service.canViewCourseMedia(7L, null, "STUDENT")).isFalse();
    }

    @Test
    void unpublishedCourseMediaIsOnlyForCreatorTeacherOrAdmin() {
        CourseMapper courseMapper = mock(CourseMapper.class);
        CourseLessonMapper lessonMapper = mock(CourseLessonMapper.class);
        CourseService service = new CourseService(courseMapper, null, lessonMapper, null, null, null);
        Course draft = course(8L, "草稿课", "required");
        draft.setStatus("draft");
        draft.setCreatedBy(16L);
        when(courseMapper.selectById(8L)).thenReturn(draft);
        CourseLesson lesson = lesson(80L, 8L, 60);
        when(lessonMapper.selectById(80L)).thenReturn(lesson);

        assertThat(service.canViewCourseMedia(8L, 16L, "TEACHER")).isTrue();
        assertThat(service.canViewCourseMedia(8L, 10L, "STUDENT")).isFalse();
        assertThat(service.canViewCourseMedia(8L, 11L, "TEACHER")).isFalse();
        assertThat(service.canViewCourseMedia(8L, 1L, "ADMIN")).isTrue();
        assertThat(service.canViewLessonMedia(80L, 16L, "TEACHER")).isTrue();
        assertThat(service.canViewLessonMedia(80L, 10L, "STUDENT")).isFalse();
    }

    private Course course(Long id, String title, String type) {
        Course course = new Course();
        course.setId(id);
        course.setTitle(title);
        course.setCourseType(type);
        course.setStatus("published");
        return course;
    }

    private CourseLesson lesson(Long id, Long courseId, Integer durationSeconds) {
        CourseLesson lesson = new CourseLesson();
        lesson.setId(id);
        lesson.setCourseId(courseId);
        lesson.setChapterId(1L);
        lesson.setTitle("视频课时");
        lesson.setLessonType("video");
        lesson.setDurationSeconds(durationSeconds);
        return lesson;
    }
}
