package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("issue")
public class Issue {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long tenantId;
    private Long meetingId;
    private Long scoreDetailId;
    private String category;
    private String description;
    private Long sourceUserId;
    private Integer status; // 0=待解决, 1=已解决
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    private LocalDateTime resolvedAt;
    private Long resolvedMeetingId;
}
