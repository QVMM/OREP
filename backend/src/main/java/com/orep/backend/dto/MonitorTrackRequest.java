package com.orep.backend.dto;

import lombok.Data;

import java.util.Map;

@Data
public class MonitorTrackRequest {
    private String source;
    private String actionType;
    private String actionName;
    private String route;
    private String pageTitle;
    private String metadata;
    private Map<String, Object> detail;
}
