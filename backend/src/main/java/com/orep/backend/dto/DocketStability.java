package com.orep.backend.dto;

import com.orep.backend.entity.AiScoreDocketRun;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class DocketStability {
    private String band;
    private int runCount;
    private String identityBand;
    private int identityRunCount;
    private String identityHeadline;
    private List<AiScoreDocketRun> runs = new ArrayList<>();
}
