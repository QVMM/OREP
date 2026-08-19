package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_score_docket")
public class AiScoreDocket {
    @TableId(type = IdType.INPUT)
    private String docketId;
    private String videoSha256;
    private String ruleVersion;
    private String ruleHash;
    private String contractVersion;
    private String trackId;
    private Boolean taskBookPublished;
    private String taskBookJson;
    private Long taskBookPublishedSessionId;
    private LocalDateTime taskBookPublishedAt;
    private LocalDateTime createdAt;
}
