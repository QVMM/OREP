package com.orep.backend.entity;

import lombok.Data;
import java.util.Date;

@Data
public class Resource {
    private Integer id;
    private String name;
    private Long fileSize;
    private String ext;
    private String filePath;
    private String category;
    private Integer uploadedBy;
    private Long teamId;
    private Date createdAt;
    private Date updatedAt;
    // 附加字段（非数据库）
    private String size;
    private String url;
    private String uploaderName;
}
