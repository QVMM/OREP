package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("track_evidence_schema")
public class TrackEvidenceSchema {
    @TableId(type = IdType.AUTO)
    private Long id;
    private String trackId;
    private String trackName;
    private String schemaVersion;
    private String schemaHash;
    private String materialTypesJson;
    private String frameTargetsJson;
    private String demoActionsJson;
    private String riskPatternsJson;
    private String thirdPartyPackagingSignalsJson;
    private String acceptableEvidenceLevelsJson;
    private String status;
    private String activeSlot;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
