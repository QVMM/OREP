package com.orep.backend.dto;

import lombok.Data;

@Data
public class AiScoreEvidenceBundleResponse {
    private Long sessionId;
    private Long snapshotId;
    private String snapshotStatus;
    private Integer mediaAssetCount;
    private Integer transcriptSegmentCount;
    private Integer frameCount;
    private Integer evidenceAnchorCount;
    private String mediaAssetHash;
    private String asrSnapshotHash;
    private String frameSnapshotHash;
    private String ocrSnapshotHash;
    private String materialSnapshotHash;
}
