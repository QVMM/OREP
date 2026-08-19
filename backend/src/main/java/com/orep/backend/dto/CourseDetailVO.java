package com.orep.backend.dto;

import com.orep.backend.entity.CourseAttachment;
import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.ArrayList;
import java.util.List;

@Data
@EqualsAndHashCode(callSuper = true)
public class CourseDetailVO extends CourseVO {
    private List<ChapterVO> chapters = new ArrayList<>();
    private List<CourseAttachment> attachments = new ArrayList<>();

    @Data
    public static class ChapterVO {
        private Long id;
        private String title;
        private Integer sortOrder;
        private List<LessonVO> lessons = new ArrayList<>();
    }

    @Data
    public static class LessonVO {
        private Long id;
        private Long chapterId;
        private String title;
        private String lessonType;
        private Integer durationSeconds;
        private String resourceUrl;
        private String videoMimeType;
        private Long videoSizeBytes;
        private Integer sortOrder;
        private Boolean completed;
        private Boolean current;
    }
}
