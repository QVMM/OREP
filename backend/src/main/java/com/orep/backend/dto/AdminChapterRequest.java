package com.orep.backend.dto;

import lombok.Data;

@Data
public class AdminChapterRequest {
    private String title;
    private Integer sortOrder;
}
