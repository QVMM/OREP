package com.orep.backend.dto;

import lombok.Data;

@Data
public class SpeakerIdentityUpdateRequest {
    private String displayName;
    private String roleName;
}
