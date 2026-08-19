package com.orep.backend.dto;

import lombok.Data;
import java.util.List;

@Data
public class ScoreSubmitRequest {
    private Long meetingId;
    private List<ScoreItemRequest> scores;

    @Data
    public static class ScoreItemRequest {
        private Long itemId;
        private Double score;
        private String comment;
    }
}
