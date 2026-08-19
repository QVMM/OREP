package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("inspire_office_document")
public class InspireOfficeDocument {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String fileKey;
    private Integer version;
    private Long ownerUserId;
    private Long ownerTenantId;
    private String title;
    private String ext;
    private String storagePath;
    private Long sizeBytes;
    /** personal | project | team */
    private String scope;
    private Long teamId;
    /** 资源中心 resource.id，项目/团队同步后写入 */
    private Integer resourceId;
    private String status;
    private LocalDateTime lastOpenedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
