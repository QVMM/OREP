package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;

@Data
@TableName("score_detail")
public class ScoreDetail {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long recordId;
    private Long itemId;
    private BigDecimal score;
    private String comment;
}
