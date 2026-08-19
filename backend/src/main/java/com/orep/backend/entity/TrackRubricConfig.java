package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("track_rubric_config")
public class TrackRubricConfig {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String trackId;
    private String trackName;
    private String rubricId;
    private String internalVersion;
    private String rubricHash;
    private String rubricPath;
    private String status;
    private String activeSlot;
    private LocalDateTime effectiveFrom;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
