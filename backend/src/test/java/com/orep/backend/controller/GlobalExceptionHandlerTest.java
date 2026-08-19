package com.orep.backend.controller;

import com.orep.backend.common.Result;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.server.ResponseStatusException;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void responseStatusExceptionPreserves403StatusCode() {
        ResponseStatusException ex = new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话");

        ResponseEntity<Result<Void>> entity = handler.handleResponseStatusException(ex);

        assertEquals(HttpStatus.FORBIDDEN, entity.getStatusCode());
        assertEquals(403, entity.getBody().getCode());
        assertEquals("无权访问该评分会话", entity.getBody().getMessage());
    }

    @Test
    void responseStatusExceptionPreserves404StatusCode() {
        ResponseStatusException ex = new ResponseStatusException(HttpStatus.NOT_FOUND, "评分会话不存在");

        ResponseEntity<Result<Void>> entity = handler.handleResponseStatusException(ex);

        assertEquals(HttpStatus.NOT_FOUND, entity.getStatusCode());
        assertEquals(404, entity.getBody().getCode());
        assertEquals("评分会话不存在", entity.getBody().getMessage());
    }

    @Test
    void responseStatusExceptionPreserves401StatusCode() {
        ResponseStatusException ex = new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");

        ResponseEntity<Result<Void>> entity = handler.handleResponseStatusException(ex);

        assertEquals(HttpStatus.UNAUTHORIZED, entity.getStatusCode());
        assertEquals(401, entity.getBody().getCode());
        assertEquals("请先登录", entity.getBody().getMessage());
    }

    @Test
    void lockedTrainingDayUsesHttp423() {
        ResponseStatusException ex = new ResponseStatusException(HttpStatus.LOCKED, "训练日尚未开放");

        ResponseEntity<Result<Void>> entity = handler.handleResponseStatusException(ex);

        assertEquals(HttpStatus.LOCKED, entity.getStatusCode());
        assertEquals(423, entity.getBody().getCode());
        assertEquals("训练日尚未开放", entity.getBody().getMessage());
    }
}
