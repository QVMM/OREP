package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("tenant")
public class Tenant {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String name;
    private String code;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
