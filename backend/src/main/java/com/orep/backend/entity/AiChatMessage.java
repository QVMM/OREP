package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("ai_chat_message")
public class AiChatMessage {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private String role;        // user / assistant
    private String content;
    private String model;       // deepseek-chat / qwen3-vl-flash
    private String routeType;   // TEXT / VISUAL
    private LocalDateTime createdAt;
}
