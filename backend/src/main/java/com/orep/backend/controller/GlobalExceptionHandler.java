package com.orep.backend.controller;

import com.orep.backend.common.Result;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.server.ResponseStatusException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ResponseStatusException.class)
    @Order(-1)
    public ResponseEntity<Result<Void>> handleResponseStatusException(ResponseStatusException e) {
        int status = e.getStatusCode().value();
        String reason = e.getReason();
        if (status >= 500) {
            log.error("submit/api ResponseStatusException status={} reason={}", status, reason, e);
        } else {
            log.warn("submit/api ResponseStatusException status={} reason={}", status, reason);
        }
        return ResponseEntity.status(e.getStatusCode()).body(Result.error(status, reason));
    }

    @ExceptionHandler(RuntimeException.class)
    public Result<Void> handleRuntimeException(RuntimeException e) {
        log.error("Unhandled runtime exception", e);
        String msg = e.getMessage();
        if (msg == null || msg.isBlank()) {
            msg = e.getClass().getSimpleName();
        }
        return Result.error(500, msg);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public Result<Void> handleIllegalArgument(IllegalArgumentException e) {
        return Result.error(400, e.getMessage());
    }
}
