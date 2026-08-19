package com.orep.backend.dto;

import lombok.Data;

@Data
public class ResolvedRubric {
    private String rubricId;
    private String rubricInternalVersion;
    private String rubricHash;
    private String rubricPath;
    private String trackId;
    private String trackName;
    private Long evidenceSchemaId;
    private String evidenceSchemaVersion;
    private String evidenceSchemaHash;
    private String materialTypesJson;
    private String frameTargetsJson;
    private String demoActionsJson;
    private String riskPatternsJson;
    private String thirdPartyPackagingSignalsJson;
    private String acceptableEvidenceLevelsJson;
}
