package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AdminChapterRequest;
import com.orep.backend.dto.AdminCourseRequest;
import com.orep.backend.dto.AdminLessonRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.dto.CourseDetailVO;
import com.orep.backend.dto.CourseVO;
import com.orep.backend.entity.Course;
import com.orep.backend.entity.CourseAttachment;
import com.orep.backend.entity.CourseChapter;
import com.orep.backend.entity.CourseLearningProgress;
import com.orep.backend.entity.CourseLesson;
import com.orep.backend.mapper.CourseAttachmentMapper;
import com.orep.backend.mapper.CourseChapterMapper;
import com.orep.backend.mapper.CourseLearningProgressMapper;
import com.orep.backend.mapper.CourseLessonMapper;
import com.orep.backend.mapper.CourseMapper;
import com.orep.backend.security.AdminAccess;
import jakarta.annotation.PostConstruct;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
public class CourseService {
    private final CourseMapper courseMapper;
    private final CourseChapterMapper chapterMapper;
    private final CourseLessonMapper lessonMapper;
    private final CourseAttachmentMapper attachmentMapper;
    private final CourseLearningProgressMapper progressMapper;
    private final JdbcTemplate jdbc;

    public CourseService(
            CourseMapper courseMapper,
            CourseChapterMapper chapterMapper,
            CourseLessonMapper lessonMapper,
            CourseAttachmentMapper attachmentMapper,
            CourseLearningProgressMapper progressMapper,
            JdbcTemplate jdbc
    ) {
        this.courseMapper = courseMapper;
        this.chapterMapper = chapterMapper;
        this.lessonMapper = lessonMapper;
        this.attachmentMapper = attachmentMapper;
        this.progressMapper = progressMapper;
        this.jdbc = jdbc;
    }

    @PostConstruct
    public void ensureSchema() {
        execute("""
                CREATE TABLE IF NOT EXISTS course (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    title VARCHAR(255) NOT NULL COMMENT '课程标题',
                    subtitle VARCHAR(255) DEFAULT NULL COMMENT '课程副标题',
                    description TEXT DEFAULT NULL COMMENT '课程简介',
                    course_type VARCHAR(32) NOT NULL DEFAULT 'required' COMMENT 'required=必修课, elective=选修课',
                    category VARCHAR(100) NOT NULL DEFAULT '人工智能' COMMENT '课程分类',
                    cover_url VARCHAR(512) DEFAULT NULL COMMENT '封面图地址',
                    accent_color VARCHAR(32) DEFAULT '#7cffb2' COMMENT '前端强调色',
                    status VARCHAR(32) NOT NULL DEFAULT 'published' COMMENT 'published=已发布, draft=草稿',
                    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
                    created_by BIGINT DEFAULT NULL COMMENT '创建者用户ID',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    KEY idx_status_sort (status, sort_order),
                    KEY idx_type (course_type),
                    KEY idx_category (category),
                    KEY idx_course_created_by (created_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程主表'
                """);
        execute("""
                CREATE TABLE IF NOT EXISTS course_chapter (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL COMMENT '课程ID',
                    title VARCHAR(255) NOT NULL COMMENT '章节标题',
                    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    KEY idx_course_sort (course_id, sort_order),
                    CONSTRAINT fk_course_chapter_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程章节表'
                """);
        execute("""
                CREATE TABLE IF NOT EXISTS course_lesson (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL COMMENT '课程ID',
                    chapter_id BIGINT NOT NULL COMMENT '章节ID',
                    title VARCHAR(255) NOT NULL COMMENT '课时标题',
                    lesson_type VARCHAR(32) NOT NULL DEFAULT 'video' COMMENT 'video=视频, document=文档',
                    duration_seconds INT NOT NULL DEFAULT 0 COMMENT '时长秒数',
                    resource_url VARCHAR(512) DEFAULT NULL COMMENT '播放或资料地址',
                    video_file_path VARCHAR(512) DEFAULT NULL COMMENT '课程视频本地相对路径',
                    video_mime_type VARCHAR(100) DEFAULT NULL COMMENT '课程视频 MIME 类型',
                    video_size_bytes BIGINT DEFAULT NULL COMMENT '课程视频大小',
                    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    KEY idx_course_sort (course_id, sort_order),
                    KEY idx_chapter_sort (chapter_id, sort_order),
                    CONSTRAINT fk_course_lesson_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
                    CONSTRAINT fk_course_lesson_chapter FOREIGN KEY (chapter_id) REFERENCES course_chapter(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程课时表'
                """);
        execute("""
                CREATE TABLE IF NOT EXISTS course_attachment (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    course_id BIGINT NOT NULL COMMENT '课程ID',
                    name VARCHAR(255) NOT NULL COMMENT '附件名称',
                    file_url VARCHAR(512) NOT NULL COMMENT '附件地址',
                    file_type VARCHAR(32) DEFAULT NULL COMMENT '附件类型',
                    file_size VARCHAR(64) DEFAULT NULL COMMENT '展示用大小',
                    sort_order INT NOT NULL DEFAULT 0 COMMENT '排序',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    KEY idx_course_sort (course_id, sort_order),
                    CONSTRAINT fk_course_attachment_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程附件表'
                """);
        execute("""
                CREATE TABLE IF NOT EXISTS course_learning_progress (
                    id BIGINT PRIMARY KEY AUTO_INCREMENT,
                    user_id BIGINT NOT NULL COMMENT '用户ID',
                    course_id BIGINT NOT NULL COMMENT '课程ID',
                    lesson_id BIGINT DEFAULT NULL COMMENT '最近学习课时ID',
                    learned_seconds INT NOT NULL DEFAULT 0 COMMENT '当前课时已学秒数',
                    progress_percent INT NOT NULL DEFAULT 0 COMMENT '课程进度百分比',
                    completed_lessons INT NOT NULL DEFAULT 0 COMMENT '已完成课时数',
                    status VARCHAR(32) NOT NULL DEFAULT 'not_started' COMMENT 'not_started, learning, completed',
                    last_learned_at DATETIME DEFAULT NULL COMMENT '最近学习时间',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_course (user_id, course_id),
                    KEY idx_user_status (user_id, status),
                    KEY idx_lesson (lesson_id),
                    CONSTRAINT fk_course_progress_course FOREIGN KEY (course_id) REFERENCES course(id) ON DELETE CASCADE,
                    CONSTRAINT fk_course_progress_lesson FOREIGN KEY (lesson_id) REFERENCES course_lesson(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程学习进度表'
                """);
        addColumn("course", "created_by", "BIGINT DEFAULT NULL COMMENT '创建者用户ID' AFTER sort_order");
        addColumn("course_lesson", "video_file_path", "VARCHAR(512) DEFAULT NULL COMMENT '课程视频本地相对路径' AFTER resource_url");
        addColumn("course_lesson", "video_mime_type", "VARCHAR(100) DEFAULT NULL COMMENT '课程视频 MIME 类型' AFTER video_file_path");
        addColumn("course_lesson", "video_size_bytes", "BIGINT DEFAULT NULL COMMENT '课程视频大小' AFTER video_mime_type");
        addIndex("course", "idx_course_created_by", "ALTER TABLE course ADD KEY idx_course_created_by (created_by)");
        addIndex("course_lesson", "idx_chapter_sort", "ALTER TABLE course_lesson ADD KEY idx_chapter_sort (chapter_id, sort_order)");
        execute("""
                UPDATE course_lesson
                SET resource_url = CONCAT('/api/courses/lessons/', id, '/stream')
                WHERE video_file_path IS NOT NULL AND video_file_path <> ''
                  AND (resource_url IS NULL OR resource_url = '' OR resource_url NOT LIKE '/api/courses/lessons/%/stream')
                """);
    }

    private void execute(String sql) {
        if (jdbc == null) return;
        try {
            jdbc.execute(sql);
        } catch (Exception ignored) {
        }
    }

    private void addColumn(String table, String column, String ddl) {
        if (jdbc == null) return;
        try {
            jdbc.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + ddl);
        } catch (Exception ignored) {
        }
    }

    private void addIndex(String table, String index, String ddl) {
        if (jdbc == null) return;
        try {
            jdbc.execute(ddl);
        } catch (Exception ignored) {
        }
    }

    public List<CourseVO> listCourses(Long userId, String filter, String category) {
        List<Course> courses = courseMapper.selectList(
                new LambdaQueryWrapper<Course>()
                        .eq(Course::getStatus, "published")
                        .eq(isCourseTypeFilter(filter), Course::getCourseType, filter)
                        .eq(category != null && !category.isBlank() && !"all".equals(category), Course::getCategory, category)
                        .orderByAsc(Course::getSortOrder)
                        .orderByDesc(Course::getCreatedAt)
        );

        if (courses.isEmpty()) return List.of();

        List<Long> courseIds = courses.stream().map(Course::getId).toList();
        Map<Long, CourseLearningProgress> progressByCourse = progressMapper.selectList(
                new LambdaQueryWrapper<CourseLearningProgress>()
                        .eq(CourseLearningProgress::getUserId, userId)
                        .in(CourseLearningProgress::getCourseId, courseIds)
        ).stream().collect(Collectors.toMap(CourseLearningProgress::getCourseId, item -> item, (a, b) -> a));

        Map<Long, CourseLesson> lessonById = loadLessonMap(courseIds);
        Map<Long, Integer> lessonCountByCourse = loadLessonCount(courseIds);

        return courses.stream()
                .map(course -> toCourseVO(
                        course,
                        progressByCourse.get(course.getId()),
                        lessonById,
                        lessonCountByCourse.getOrDefault(course.getId(), 0)
                ))
                .filter(course -> matchesProgressFilter(course, filter))
                .toList();
    }

    public List<Course> listAdminCourses(Long userId, String role) {
        return courseMapper.selectList(
                new LambdaQueryWrapper<Course>()
                        .eq(isTeacher(role), Course::getCreatedBy, userId)
                        .orderByAsc(Course::getSortOrder)
                        .orderByDesc(Course::getCreatedAt)
        );
    }

    public Course createCourse(AdminCourseRequest request, Long creatorId) {
        Course course = new Course();
        applyCourseRequest(course, request);
        course.setCreatedBy(creatorId);
        if (course.getStatus() == null || course.getStatus().isBlank()) course.setStatus("draft");
        if (course.getCourseType() == null || course.getCourseType().isBlank()) course.setCourseType("required");
        if (course.getCategory() == null || course.getCategory().isBlank()) course.setCategory("人工智能");
        if (course.getAccentColor() == null || course.getAccentColor().isBlank()) course.setAccentColor("#7cffb2");
        if (course.getSortOrder() == null) course.setSortOrder(0);
        courseMapper.insert(course);
        return course;
    }

    public Course updateCourse(Long id, AdminCourseRequest request, Long userId, String role) {
        Course course = courseMapper.selectById(id);
        if (!canAccessAdminCourse(course, userId, role)) return null;
        applyCourseRequest(course, request);
        courseMapper.updateById(course);
        return course;
    }

    public Course updateCourseCover(Long id, String coverUrl, Long userId, String role) {
        Course course = courseMapper.selectById(id);
        if (!canAccessAdminCourse(course, userId, role)) return null;
        course.setCoverUrl(coverUrl);
        courseMapper.updateById(course);
        return course;
    }

    public boolean deleteCourse(Long id, Long userId, String role) {
        Course course = courseMapper.selectById(id);
        if (!canAccessAdminCourse(course, userId, role)) return false;
        return courseMapper.deleteById(id) > 0;
    }

    @Transactional
    public BatchDeleteResult deleteCourses(List<Long> ids, Long userId, String role) {
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> normalizedIds = normalizeIds(ids);
        result.setRequested(normalizedIds.size());
        for (Long id : normalizedIds) {
            if (deleteCourse(id, userId, role)) {
                result.addDeleted();
            } else {
                result.addFailure(id, "课程不存在或无权删除");
            }
        }
        return result;
    }

    public CourseChapter createChapter(Long courseId, AdminChapterRequest request, Long userId, String role) {
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return null;
        CourseChapter chapter = new CourseChapter();
        chapter.setCourseId(courseId);
        chapter.setTitle(nonBlank(request.getTitle(), "新章节"));
        chapter.setSortOrder(request.getSortOrder() == null ? 0 : request.getSortOrder());
        chapterMapper.insert(chapter);
        return chapter;
    }

    public CourseChapter updateChapter(Long courseId, Long chapterId, AdminChapterRequest request, Long userId, String role) {
        CourseChapter chapter = chapterMapper.selectById(chapterId);
        if (chapter == null || !Objects.equals(chapter.getCourseId(), courseId)) return null;
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return null;
        chapter.setTitle(nonBlank(request.getTitle(), chapter.getTitle()));
        if (request.getSortOrder() != null) chapter.setSortOrder(request.getSortOrder());
        chapterMapper.updateById(chapter);
        return chapter;
    }

    public boolean deleteChapter(Long courseId, Long chapterId, Long userId, String role) {
        CourseChapter chapter = chapterMapper.selectById(chapterId);
        if (chapter == null || !Objects.equals(chapter.getCourseId(), courseId)) return false;
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return false;
        return chapterMapper.deleteById(chapterId) > 0;
    }

    public CourseLesson createLesson(Long courseId, AdminLessonRequest request, Long userId, String role) {
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return null;
        CourseChapter chapter = chapterMapper.selectOne(
                new LambdaQueryWrapper<CourseChapter>()
                        .eq(CourseChapter::getId, request.getChapterId())
                        .eq(CourseChapter::getCourseId, courseId)
        );
        if (chapter == null) return null;

        CourseLesson lesson = new CourseLesson();
        lesson.setCourseId(courseId);
        lesson.setChapterId(chapter.getId());
        lesson.setTitle(nonBlank(request.getTitle(), "新课时"));
        lesson.setLessonType(nonBlank(request.getLessonType(), "video"));
        lesson.setDurationSeconds(request.getDurationSeconds() == null ? 0 : request.getDurationSeconds());
        lesson.setSortOrder(request.getSortOrder() == null ? 0 : request.getSortOrder());
        lessonMapper.insert(lesson);
        return lesson;
    }

    public CourseLesson updateLesson(Long courseId, Long lessonId, AdminLessonRequest request, Long userId, String role) {
        CourseLesson lesson = lessonMapper.selectById(lessonId);
        if (lesson == null || !Objects.equals(lesson.getCourseId(), courseId)) return null;
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return null;
        CourseChapter chapter = chapterMapper.selectOne(
                new LambdaQueryWrapper<CourseChapter>()
                        .eq(CourseChapter::getId, request.getChapterId())
                        .eq(CourseChapter::getCourseId, courseId)
        );
        if (chapter == null) return null;
        lesson.setChapterId(chapter.getId());
        lesson.setTitle(nonBlank(request.getTitle(), lesson.getTitle()));
        lesson.setLessonType(nonBlank(request.getLessonType(), lesson.getLessonType()));
        if (request.getDurationSeconds() != null) lesson.setDurationSeconds(Math.max(0, request.getDurationSeconds()));
        if (request.getSortOrder() != null) lesson.setSortOrder(request.getSortOrder());
        lessonMapper.updateById(lesson);
        return lesson;
    }

    public boolean deleteLesson(Long courseId, Long lessonId, Long userId, String role) {
        CourseLesson lesson = lessonMapper.selectById(lessonId);
        if (lesson == null || !Objects.equals(lesson.getCourseId(), courseId)) return false;
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return false;
        return lessonMapper.deleteById(lessonId) > 0;
    }

    public CourseLesson attachLessonVideo(Long lessonId, String videoFilePath, String videoMimeType, Long videoSizeBytes, Integer durationSeconds, Long userId, String role) {
        CourseLesson lesson = lessonMapper.selectById(lessonId);
        if (lesson == null) return null;
        if (!canAccessAdminCourse(courseMapper.selectById(lesson.getCourseId()), userId, role)) return null;
        lesson.setVideoFilePath(videoFilePath);
        lesson.setVideoMimeType(nonBlank(videoMimeType, "video/mp4"));
        lesson.setVideoSizeBytes(videoSizeBytes == null ? 0L : videoSizeBytes);
        if (durationSeconds != null && durationSeconds >= 0) {
            lesson.setDurationSeconds(durationSeconds);
        }
        lesson.setLessonType("video");
        lesson.setResourceUrl("/api/courses/lessons/" + lessonId + "/stream");
        lessonMapper.updateById(lesson);
        return lesson;
    }

    public CourseAttachment createAttachment(Long courseId, String name, String fileUrl, String fileType, String fileSize, Integer sortOrder, Long userId, String role) {
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return null;
        CourseAttachment attachment = new CourseAttachment();
        attachment.setCourseId(courseId);
        attachment.setName(nonBlank(name, "课程附件"));
        attachment.setFileUrl(fileUrl);
        attachment.setFileType(fileType);
        attachment.setFileSize(fileSize);
        attachment.setSortOrder(sortOrder == null ? 0 : sortOrder);
        attachmentMapper.insert(attachment);
        return attachment;
    }

    public boolean deleteAttachment(Long courseId, Long attachmentId, Long userId, String role) {
        if (!canAccessAdminCourse(courseMapper.selectById(courseId), userId, role)) return false;
        CourseAttachment attachment = attachmentMapper.selectById(attachmentId);
        if (attachment == null || !Objects.equals(attachment.getCourseId(), courseId)) return false;
        return attachmentMapper.deleteById(attachmentId) > 0;
    }

    @Transactional
    public BatchDeleteResult deleteAttachments(Long courseId, List<Long> ids, Long userId, String role) {
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> normalizedIds = normalizeIds(ids);
        result.setRequested(normalizedIds.size());
        for (Long id : normalizedIds) {
            if (deleteAttachment(courseId, id, userId, role)) {
                result.addDeleted();
            } else {
                result.addFailure(id, "附件不存在或无权删除");
            }
        }
        return result;
    }

    public CourseLesson getLesson(Long lessonId) {
        return lessonMapper.selectById(lessonId);
    }

    public boolean canViewLessonMedia(Long lessonId, Long userId, String role) {
        if (lessonId == null) {
            return false;
        }
        CourseLesson lesson = lessonMapper.selectById(lessonId);
        if (lesson == null) {
            return false;
        }
        return canViewCourseMedia(lesson.getCourseId(), userId, role);
    }

    public boolean canViewCourseMedia(Long courseId, Long userId, String role) {
        if (courseId == null || userId == null) {
            return false;
        }
        Course course = courseMapper.selectById(courseId);
        if (course == null) {
            return false;
        }
        if ("published".equalsIgnoreCase(String.valueOf(course.getStatus()))) {
            return true;
        }
        String normalized = AdminAccess.normalizeRole(role);
        if ("ADMIN".equals(normalized) || "SCHOOL_ADMIN".equals(normalized) || "SUPER_ADMIN".equals(normalized)) {
            return true;
        }
        return isTeacher(role) && Objects.equals(course.getCreatedBy(), userId);
    }

    public CourseDetailVO getCourseDetail(Long courseId, Long userId) {
        Course course = courseMapper.selectOne(
                new LambdaQueryWrapper<Course>()
                        .eq(Course::getId, courseId)
                        .eq(Course::getStatus, "published")
        );
        if (course == null) return null;

        List<CourseChapter> chapters = chapterMapper.selectList(
                new LambdaQueryWrapper<CourseChapter>()
                        .eq(CourseChapter::getCourseId, courseId)
                        .orderByAsc(CourseChapter::getSortOrder)
        );
        List<CourseLesson> lessons = lessonMapper.selectList(
                new LambdaQueryWrapper<CourseLesson>()
                        .eq(CourseLesson::getCourseId, courseId)
                        .orderByAsc(CourseLesson::getSortOrder)
        );
        CourseLearningProgress progress = getProgress(userId, courseId);

        CourseDetailVO detail = new CourseDetailVO();
        copyCourseFields(detail, course, progress, lessons.stream().collect(Collectors.toMap(CourseLesson::getId, item -> item, (a, b) -> a)), lessons.size());
        detail.setChapters(toChapterVOs(chapters, lessons, progress));
        detail.setAttachments(attachmentMapper.selectList(
                new LambdaQueryWrapper<CourseAttachment>()
                        .eq(CourseAttachment::getCourseId, courseId)
                        .orderByAsc(CourseAttachment::getSortOrder)
        ));
        return detail;
    }

    public CourseDetailVO getAdminCourseDetail(Long courseId, Long userId, String role) {
        Course course = courseMapper.selectById(courseId);
        if (!canAccessAdminCourse(course, userId, role)) return null;
        List<CourseChapter> chapters = chapterMapper.selectList(
                new LambdaQueryWrapper<CourseChapter>()
                        .eq(CourseChapter::getCourseId, courseId)
                        .orderByAsc(CourseChapter::getSortOrder)
        );
        List<CourseLesson> lessons = lessonMapper.selectList(
                new LambdaQueryWrapper<CourseLesson>()
                        .eq(CourseLesson::getCourseId, courseId)
                        .orderByAsc(CourseLesson::getSortOrder)
        );
        CourseDetailVO detail = new CourseDetailVO();
        copyCourseFields(detail, course, null, lessons.stream().collect(Collectors.toMap(CourseLesson::getId, item -> item, (a, b) -> a)), lessons.size());
        detail.setChapters(toChapterVOs(chapters, lessons, null));
        detail.setAttachments(attachmentMapper.selectList(
                new LambdaQueryWrapper<CourseAttachment>()
                        .eq(CourseAttachment::getCourseId, courseId)
                        .orderByAsc(CourseAttachment::getSortOrder)
        ));
        return detail;
    }

    public CourseVO saveProgress(Long userId, Long courseId, Long lessonId, Integer learnedSeconds) {
        Course course = courseMapper.selectById(courseId);
        CourseLesson lesson = lessonMapper.selectOne(
                new LambdaQueryWrapper<CourseLesson>()
                        .eq(CourseLesson::getId, lessonId)
                        .eq(CourseLesson::getCourseId, courseId)
        );
        if (course == null || lesson == null) return null;

        CourseLearningProgress progress = getOrCreateProgress(userId, courseId);
        Integer safeLearnedSeconds = clampLearnedSeconds(progress, lesson, lessonId, learnedSeconds);
        progress.setLessonId(lessonId);
        progress.setLearnedSeconds(safeLearnedSeconds);
        progress.setLastLearnedAt(LocalDateTime.now());
        if (!"completed".equals(progress.getStatus())) {
            progress.setStatus("learning");
            int totalLessons = Math.max(1, lessonMapper.selectCount(
                    new LambdaQueryWrapper<CourseLesson>().eq(CourseLesson::getCourseId, courseId)
            ).intValue());
            int completedLessons = progress.getCompletedLessons() == null ? 0 : progress.getCompletedLessons();
            int duration = Math.max(1, lesson.getDurationSeconds() == null ? 0 : lesson.getDurationSeconds());
            double currentRatio = Math.min(1.0, progress.getLearnedSeconds() / (double) duration);
            int percent = Math.min(99, (int) Math.round((completedLessons + currentRatio) * 100.0 / totalLessons));
            progress.setProgressPercent(Math.max(1, Math.max(progress.getProgressPercent() == null ? 0 : progress.getProgressPercent(), percent)));
        }
        progressMapper.updateById(progress);
        return getCourseVO(courseId, userId);
    }

    public CourseVO completeLesson(Long userId, Long lessonId) {
        CourseLesson lesson = lessonMapper.selectById(lessonId);
        if (lesson == null) return null;

        Long courseId = lesson.getCourseId();
        CourseLearningProgress progress = getOrCreateProgress(userId, courseId);
        if (!hasEnoughWatchTime(progress, lesson, lessonId)) {
            throw new IllegalStateException("学习时长不足，暂不能完成课时");
        }
        int totalLessons = Math.max(1, lessonMapper.selectCount(
                new LambdaQueryWrapper<CourseLesson>().eq(CourseLesson::getCourseId, courseId)
        ).intValue());

        int completedLessons = Math.max(progress.getCompletedLessons() == null ? 0 : progress.getCompletedLessons(), lessonSortPosition(courseId, lessonId));
        int percent = Math.min(100, (int) Math.round(completedLessons * 100.0 / totalLessons));

        progress.setLessonId(lessonId);
        progress.setLearnedSeconds(lesson.getDurationSeconds() == null ? 0 : lesson.getDurationSeconds());
        progress.setCompletedLessons(completedLessons);
        progress.setProgressPercent(percent);
        progress.setStatus(percent >= 100 ? "completed" : "learning");
        progress.setLastLearnedAt(LocalDateTime.now());
        progressMapper.updateById(progress);
        return getCourseVO(courseId, userId);
    }

    private Integer clampLearnedSeconds(CourseLearningProgress progress, CourseLesson lesson, Long lessonId, Integer learnedSeconds) {
        int duration = Math.max(0, lesson.getDurationSeconds() == null ? 0 : lesson.getDurationSeconds());
        int requested = Math.max(0, learnedSeconds == null ? 0 : learnedSeconds);
        if (duration > 0) {
            requested = Math.min(requested, duration);
        }

        boolean sameLesson = Objects.equals(progress.getLessonId(), lessonId);
        int previous = sameLesson ? Math.max(0, progress.getLearnedSeconds() == null ? 0 : progress.getLearnedSeconds()) : 0;
        if (requested <= previous) {
            return previous;
        }

        int allowedIncrease = 15;
        if (sameLesson && progress.getLastLearnedAt() != null) {
            long elapsedSeconds = Math.max(0, Duration.between(progress.getLastLearnedAt(), LocalDateTime.now()).getSeconds());
            allowedIncrease = Math.max(15, (int) Math.ceil(elapsedSeconds * 1.35));
        }
        return Math.min(requested, previous + allowedIncrease);
    }

    private boolean hasEnoughWatchTime(CourseLearningProgress progress, CourseLesson lesson, Long lessonId) {
        int duration = Math.max(0, lesson.getDurationSeconds() == null ? 0 : lesson.getDurationSeconds());
        if (duration == 0) return true;
        if (!Objects.equals(progress.getLessonId(), lessonId)) return false;
        int learnedSeconds = Math.max(0, progress.getLearnedSeconds() == null ? 0 : progress.getLearnedSeconds());
        int requiredSeconds = Math.max(1, (int) Math.ceil(duration * 0.9));
        return learnedSeconds >= requiredSeconds;
    }

    private CourseVO getCourseVO(Long courseId, Long userId) {
        Course course = courseMapper.selectById(courseId);
        if (course == null) return null;
        List<CourseLesson> lessons = lessonMapper.selectList(
                new LambdaQueryWrapper<CourseLesson>().eq(CourseLesson::getCourseId, courseId)
        );
        Map<Long, CourseLesson> lessonById = lessons.stream().collect(Collectors.toMap(CourseLesson::getId, item -> item, (a, b) -> a));
        return toCourseVO(course, getProgress(userId, courseId), lessonById, lessons.size());
    }

    private CourseLearningProgress getProgress(Long userId, Long courseId) {
        if (userId == null || courseId == null) return null;
        return progressMapper.selectOne(
                new LambdaQueryWrapper<CourseLearningProgress>()
                        .eq(CourseLearningProgress::getUserId, userId)
                        .eq(CourseLearningProgress::getCourseId, courseId)
        );
    }

    private CourseLearningProgress getOrCreateProgress(Long userId, Long courseId) {
        CourseLearningProgress progress = getProgress(userId, courseId);
        if (progress != null) return progress;

        progress = new CourseLearningProgress();
        progress.setUserId(userId);
        progress.setCourseId(courseId);
        progress.setLearnedSeconds(0);
        progress.setProgressPercent(0);
        progress.setCompletedLessons(0);
        progress.setStatus("not_started");
        progress.setLastLearnedAt(LocalDateTime.now());
        progressMapper.insert(progress);
        return progress;
    }

    private CourseVO toCourseVO(Course course, CourseLearningProgress progress, Map<Long, CourseLesson> lessonById, int totalLessons) {
        CourseVO vo = new CourseVO();
        copyCourseFields(vo, course, progress, lessonById, totalLessons);
        return vo;
    }

    private void copyCourseFields(CourseVO vo, Course course, CourseLearningProgress progress, Map<Long, CourseLesson> lessonById, int totalLessons) {
        vo.setId(course.getId());
        vo.setTitle(course.getTitle());
        vo.setSubtitle(course.getSubtitle());
        vo.setDescription(course.getDescription());
        vo.setCourseType(course.getCourseType());
        vo.setCourseTypeLabel("elective".equals(course.getCourseType()) ? "选修课" : "必修课");
        vo.setCategory(course.getCategory());
        vo.setCoverUrl(course.getCoverUrl());
        vo.setAccentColor(course.getAccentColor());
        vo.setProgressPercent(progress == null || progress.getProgressPercent() == null ? 0 : progress.getProgressPercent());
        vo.setLearningStatus(progress == null ? "not_started" : normalizeStatus(progress.getStatus()));
        vo.setCurrentLessonId(progress == null ? null : progress.getLessonId());
        CourseLesson currentLesson = progress == null ? null : lessonById.get(progress.getLessonId());
        vo.setCurrentLessonTitle(currentLesson == null ? null : currentLesson.getTitle());
        vo.setLearnedSeconds(progress == null || progress.getLearnedSeconds() == null ? 0 : progress.getLearnedSeconds());
        vo.setTotalLessons(totalLessons);
        vo.setCompletedLessons(progress == null || progress.getCompletedLessons() == null ? 0 : progress.getCompletedLessons());
    }

    private List<CourseDetailVO.ChapterVO> toChapterVOs(List<CourseChapter> chapters, List<CourseLesson> lessons, CourseLearningProgress progress) {
        Map<Long, List<CourseLesson>> lessonsByChapter = lessons.stream()
                .collect(Collectors.groupingBy(CourseLesson::getChapterId));
        int completedLessons = progress == null || progress.getCompletedLessons() == null ? 0 : progress.getCompletedLessons();
        Long currentLessonId = progress == null ? null : progress.getLessonId();

        return chapters.stream().map(chapter -> {
            CourseDetailVO.ChapterVO chapterVO = new CourseDetailVO.ChapterVO();
            chapterVO.setId(chapter.getId());
            chapterVO.setTitle(chapter.getTitle());
            chapterVO.setSortOrder(chapter.getSortOrder());
            List<CourseLesson> chapterLessons = lessonsByChapter.getOrDefault(chapter.getId(), List.of());
            chapterVO.setLessons(chapterLessons.stream()
                    .sorted(Comparator.comparing(CourseLesson::getSortOrder, Comparator.nullsLast(Integer::compareTo)))
                    .map(lesson -> {
                        CourseDetailVO.LessonVO lessonVO = new CourseDetailVO.LessonVO();
                        lessonVO.setId(lesson.getId());
                        lessonVO.setChapterId(lesson.getChapterId());
                        lessonVO.setTitle(lesson.getTitle());
                        lessonVO.setLessonType(lesson.getLessonType());
                        lessonVO.setDurationSeconds(lesson.getDurationSeconds());
                        lessonVO.setResourceUrl(lesson.getResourceUrl());
                        lessonVO.setVideoMimeType(lesson.getVideoMimeType());
                        lessonVO.setVideoSizeBytes(lesson.getVideoSizeBytes());
                        lessonVO.setSortOrder(lesson.getSortOrder());
                        lessonVO.setCompleted(lessonSortPosition(lesson.getCourseId(), lesson.getId()) <= completedLessons);
                        lessonVO.setCurrent(Objects.equals(currentLessonId, lesson.getId()));
                        return lessonVO;
                    })
                    .toList());
            return chapterVO;
        }).toList();
    }

    private Map<Long, CourseLesson> loadLessonMap(List<Long> courseIds) {
        if (lessonMapper == null || courseIds == null || courseIds.isEmpty()) return new HashMap<>();
        return lessonMapper.selectList(
                new LambdaQueryWrapper<CourseLesson>().in(CourseLesson::getCourseId, courseIds)
        ).stream().collect(Collectors.toMap(CourseLesson::getId, item -> item, (a, b) -> a));
    }

    private Map<Long, Integer> loadLessonCount(List<Long> courseIds) {
        if (lessonMapper == null || courseIds == null || courseIds.isEmpty()) return new HashMap<>();
        return lessonMapper.selectList(
                new LambdaQueryWrapper<CourseLesson>().in(CourseLesson::getCourseId, courseIds)
        ).stream().collect(Collectors.groupingBy(CourseLesson::getCourseId, Collectors.collectingAndThen(Collectors.counting(), Long::intValue)));
    }

    private int lessonSortPosition(Long courseId, Long lessonId) {
        List<CourseLesson> lessons = lessonMapper.selectList(
                new LambdaQueryWrapper<CourseLesson>()
                        .eq(CourseLesson::getCourseId, courseId)
                        .orderByAsc(CourseLesson::getSortOrder)
        );
        for (int i = 0; i < lessons.size(); i++) {
            if (Objects.equals(lessons.get(i).getId(), lessonId)) return i + 1;
        }
        return 0;
    }

    private boolean isCourseTypeFilter(String filter) {
        return "required".equals(filter) || "elective".equals(filter);
    }

    private boolean matchesProgressFilter(CourseVO course, String filter) {
        if ("completed".equals(filter)) return "completed".equals(course.getLearningStatus());
        if ("unfinished".equals(filter) || "not_completed".equals(filter)) return !"completed".equals(course.getLearningStatus());
        return true;
    }

    private boolean canAccessAdminCourse(Course course, Long userId, String role) {
        if (course == null) return false;
        if (!isTeacher(role)) return true;
        return userId != null && Objects.equals(course.getCreatedBy(), userId);
    }

    private boolean isTeacher(String role) {
        return "TEACHER".equals(AdminAccess.normalizeRole(role));
    }

    private String normalizeStatus(String status) {
        if ("completed".equals(status) || "learning".equals(status)) return status;
        return "not_started";
    }

    private void applyCourseRequest(Course course, AdminCourseRequest request) {
        course.setTitle(nonBlank(request.getTitle(), course.getTitle()));
        course.setSubtitle(request.getSubtitle());
        course.setDescription(request.getDescription());
        course.setCourseType(nonBlank(request.getCourseType(), course.getCourseType()));
        course.setCategory(nonBlank(request.getCategory(), course.getCategory()));
        course.setCoverUrl(request.getCoverUrl());
        course.setAccentColor(nonBlank(request.getAccentColor(), course.getAccentColor()));
        course.setStatus(nonBlank(request.getStatus(), course.getStatus()));
        if (request.getSortOrder() != null) course.setSortOrder(request.getSortOrder());
    }

    private String nonBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private List<Long> normalizeIds(List<Long> ids) {
        if (ids == null) return List.of();
        return ids.stream().filter(Objects::nonNull).distinct().toList();
    }
}
