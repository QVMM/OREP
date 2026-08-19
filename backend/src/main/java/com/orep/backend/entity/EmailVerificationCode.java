package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("email_verification_code")
public class EmailVerificationCode {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String email;
    private String code;
    private LocalDateTime expiredAt;
    private Boolean used;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
