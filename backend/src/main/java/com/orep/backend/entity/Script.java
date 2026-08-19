package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("script")
public class Script {
    @TableId(type = IdType.AUTO)
    private Long id;
    /** 历史兼容字段；PPT 讲稿不依赖会议 ID。 */
    private Long meetingId;
    private String title;
    /** JSON: 章节和步骤数据 */
    private String content;
    /** JSON: 团队角色列表 */
    private String roles;
    /** 来源: manual / ppt */
    private String sourceType;
    /** 关联 PPT 生成任务 ID */
    private String pptJobId;
    /** 绑定的智能文档改稿工作台 */
    private Long sdocDocumentId;
    /** 同步状态: synced / page_newer / script_newer / conflict */
    private String syncStatus;
    /** 内容版本号 */
    private Integer contentVersion;
    /** 最近同步时间 */
    private LocalDateTime lastSyncedAt;
    private Long createdBy;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}
