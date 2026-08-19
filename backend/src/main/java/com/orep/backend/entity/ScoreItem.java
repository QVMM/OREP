package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.math.BigDecimal;

@Data
@TableName("score_item")
public class ScoreItem {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long templateId;
    private String category;
    private String name;
    private BigDecimal maxScore;
    private String description;
    private Integer sortOrder;
}
