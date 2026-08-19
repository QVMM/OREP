package com.orep.backend.dto;

import lombok.Data;

import java.util.List;

@Data
public class BatchDeleteRequest {
    private List<Long> ids;
}
