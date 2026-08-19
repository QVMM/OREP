package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("ai_jury_member")
public class AiJuryMember {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long jurySessionId;
    private Long personaId;
    private String personaCode;
    private Integer seatNo;
    private String displayName;
    private String roleLabel;
    private LocalDateTime createdAt;
}
