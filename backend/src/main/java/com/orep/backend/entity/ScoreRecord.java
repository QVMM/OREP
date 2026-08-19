package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("score_record")
public class ScoreRecord {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long tenantId;
    private Long meetingId;
    private Long userId;
    private BigDecimal totalScore;
    private LocalDateTime submittedAt;
}
