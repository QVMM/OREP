package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ppt_script_page")
public class PptScriptPage {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String jobId;
    private Integer pageIndex;
    private String pageName;
    private String pageTitle;
    private String notes;
    private String documentJson;
    private String source;
    private Boolean manualEdited;
    private Long scriptId;
    private String scriptStepId;
    private String contentHash;
    private Integer version;
    private String syncState;
    private LocalDateTime lastSyncedAt;
    private Long createdBy;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
