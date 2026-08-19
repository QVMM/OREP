package com.orep.backend.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Data
public class BatchDeleteResult {
    private int requested;
    private int deleted;
    private List<Failure> failed = new ArrayList<>();

    public void addDeleted() {
        deleted++;
    }

    public void addFailure(Long id, String reason) {
        Failure failure = new Failure();
        failure.setId(id);
        failure.setReason(reason);
        failed.add(failure);
    }

    @Data
    public static class Failure {
        private Long id;
        private String reason;
    }
}
