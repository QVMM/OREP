package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_jury_session")
public class AiJurySession {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long meetingId;
    private Long scoringSessionId;
    private Long baseReportId;
    private String seed;
    private String standardVersion;
    private String personaPoolVersion;
    private Integer judgeCount;
    private String status;
    private BigDecimal officialScore;
    private BigDecimal juryTrimmedAvg;
    private BigDecimal juryRawAvg;
    private BigDecimal highestScore;
    private BigDecimal lowestScore;
    private BigDecimal scoreDiffFromOfficial;
    private String evidenceSnapshotPath;
    private String resultPath;
    private String errorMessage;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
