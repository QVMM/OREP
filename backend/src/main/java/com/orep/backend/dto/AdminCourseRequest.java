package com.orep.backend.dto;

import lombok.Data;

@Data
public class AdminCourseRequest {
    private String title;
    private String subtitle;
    private String description;
    private String courseType;
    private String category;
    private String coverUrl;
    private String accentColor;
    private String status;
    private Integer sortOrder;
}
