package com.orep.backend.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class TaskBookItem {
    private String title;
    private String goal;
    private List<String> steps = new ArrayList<>();
    private String acceptance;
    private String evidenceNeeded;
    private String expectedGain;
    private String ownerRole;
    private String dueHint;
    private List<String> sourceRefs = new ArrayList<>();
    private String hungEvidence;
    private String hungAt;
    private Long hungByUserId;
}
