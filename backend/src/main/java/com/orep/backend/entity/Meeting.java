package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("meeting")
public class Meeting {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long tenantId;
    private String title;
    private Long creatorId;
    private String meetingCode;
    private String meetingPassword;
    private String jitsiRoomId;
    private String status; // CREATED, RUNNING, ENDED
    private Integer durationMinutes;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private LocalDateTime countdownEndAt;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
