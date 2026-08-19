package com.orep.backend.service.roadshow;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.service.ScriptScoreReviseService;
import com.orep.backend.service.ScriptService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class JudgePathServicePrintTest {

    @Test
    void printConflictsWhenHolesOpen() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForList(anyString(), eq(1L))).thenReturn(List.of(Map.of(
                "id", 1L,
                "created_by", 9L,
                "status", "compiled",
                "path_json", "{\"holes\":[{\"id\":\"h1\",\"acked\":false}],\"propositions\":[]}"
        )));
        JudgePathService service = new JudgePathService(
                mock(ScriptService.class),
                mock(ScriptScoreReviseService.class),
                jdbc,
                new ObjectMapper()
        );
        ResponseStatusException ex = assertThrows(ResponseStatusException.class, () -> service.print(1L, 9L));
        assertEquals(HttpStatus.CONFLICT, ex.getStatusCode());
    }
}
