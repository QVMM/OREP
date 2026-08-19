package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_judge_persona")
public class AiJudgePersona {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String code;
    private String name;
    private String shortLabel;
    private String focusDimensionsJson;
    private String judgeProfileJson;
    private String rubricFocusJson;
    private String scoringBiasJson;
    private String promptModifier;
    private String description;
    private Boolean enabled;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
