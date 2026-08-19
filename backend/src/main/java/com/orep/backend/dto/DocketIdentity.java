package com.orep.backend.dto;

import lombok.Data;

@Data
public class DocketIdentity {
    private String videoSha256;
    private String ruleVersion;
    private String ruleHash;
    private String contractVersion;
    private String trackId;
}
