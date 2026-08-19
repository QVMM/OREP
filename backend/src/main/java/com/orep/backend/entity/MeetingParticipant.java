package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("meeting_participant")
public class MeetingParticipant {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long meetingId;
    private Long userId;
    private LocalDateTime joinedAt;
    private LocalDateTime leftAt;
    private Integer durationSeconds; // 参与时长（秒），离开时计算写入
}
