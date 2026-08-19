package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("ai_chat_session")
public class AiChatSession {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long meetingId;
    private String sessionKey;
    private String projectName;
    private String status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
