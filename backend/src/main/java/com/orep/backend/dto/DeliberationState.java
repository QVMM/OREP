package com.orep.backend.dto;

import lombok.Data;

@Data
public class DeliberationState {
    private String stage;
    private boolean teacherConfirmed;
    private boolean finalized;
    private boolean challengeIncomplete;
    private String challengeNote;
    private String headline;
}
