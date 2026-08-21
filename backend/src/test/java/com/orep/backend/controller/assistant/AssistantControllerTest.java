package com.orep.backend.controller.assistant;

import com.orep.backend.service.assistant.AssistantActionService;
import com.orep.backend.service.assistant.AssistantService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

/**
 * Traces 小启 client URLs (assistantClient.js) to controller mappings.
 * A 404 here is the axios "Request failed with status code 404" on the 小启 page.
 */
class AssistantControllerTest {
    private AssistantService service;
    private AssistantActionService actionService;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        service = mock(AssistantService.class);
        actionService = mock(AssistantActionService.class);
        mvc = standaloneSetup(new AssistantController(service, actionService)).build();
    }

    @Test
    void pageLoadGetsHitExistingRoutes() throws Exception {
        when(service.listSessions(eq(7L), eq(21L), eq(null), eq(0), eq(50)))
                .thenReturn(List.of(Map.of("id", 3L, "title", "新对话")));
        when(service.listFolders(7L, 21L)).thenReturn(List.of(Map.of("id", 1L, "slug", "script")));
        when(service.listMemories(7L, 21L)).thenReturn(List.of());
        when(service.myTeams(7L, 21L, "STUDENT")).thenReturn(List.of());
        when(service.listSkills("student")).thenReturn(List.of(Map.of("name", "opening", "slash", "开场")));

        mvc.perform(get("/api/assistant/sessions").param("page", "0").param("size", "50")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L).requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].id").value(3));

        mvc.perform(get("/api/assistant/folders")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].slug").value("script"));

        mvc.perform(get("/api/assistant/memories")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L))
                .andExpect(status().isOk());

        mvc.perform(get("/api/assistant/teams")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L).requestAttr("role", "STUDENT"))
                .andExpect(status().isOk());

        mvc.perform(get("/api/assistant/skills").param("audience", "student"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].slash").value("开场"));

        mvc.perform(get("/api/assistant/v1/skills").param("audience", "student"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data[0].slash").value("开场"));
    }

    @Test
    void createSessionHitsExistingRoute() throws Exception {
        when(service.createSession(eq(7L), eq(21L), eq("STUDENT"), anyMap()))
                .thenReturn(Map.of("id", 9L, "title", "新对话"));

        mvc.perform(post("/api/assistant/sessions")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L).requestAttr("role", "STUDENT")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(9));
    }

    @Test
    void streamMessageColonPathIsMapped() throws Exception {
        when(service.streamMessage(eq(9L), eq(7L), eq(21L), eq("STUDENT"), anyMap()))
                .thenReturn(new SseEmitter(0L));

        mvc.perform(post("/api/assistant/sessions/9/messages:stream")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L).requestAttr("role", "STUDENT")
                        .contentType(MediaType.APPLICATION_JSON)
                        .accept(MediaType.TEXT_EVENT_STREAM)
                        .content("{\"content\":\"你好\"}"))
                .andExpect(status().isOk());

        verify(service).streamMessage(eq(9L), eq(7L), eq(21L), eq("STUDENT"), any());
    }

    @Test
    void streamMessageSlashPathIsMapped() throws Exception {
        when(service.streamMessage(eq(9L), eq(7L), eq(21L), eq("STUDENT"), anyMap()))
                .thenReturn(new SseEmitter(0L));

        mvc.perform(post("/api/assistant/sessions/9/messages/stream")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L).requestAttr("role", "STUDENT")
                        .contentType(MediaType.APPLICATION_JSON)
                        .accept(MediaType.TEXT_EVENT_STREAM)
                        .content("{\"content\":\"你好\"}"))
                .andExpect(status().isOk());
    }

    @Test
    void streamMessagePlainPathIsMappedWhenColonStripped() throws Exception {
        when(service.streamMessage(eq(9L), eq(7L), eq(21L), eq("STUDENT"), anyMap()))
                .thenReturn(new SseEmitter(0L));

        mvc.perform(post("/api/assistant/sessions/9/messages")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L).requestAttr("role", "STUDENT")
                        .contentType(MediaType.APPLICATION_JSON)
                        .accept(MediaType.TEXT_EVENT_STREAM)
                        .content("{\"content\":\"你好\"}"))
                .andExpect(status().isOk());
    }

    @Test
    void regenerateAndSubscribeSlashPathsAreMapped() throws Exception {
        when(service.regenerate(eq(9L), eq(44L), eq(7L), eq(21L), eq("STUDENT")))
                .thenReturn(new SseEmitter(0L));
        when(service.subscribeRun(eq(8L), eq(7L), eq(21L)))
                .thenReturn(new SseEmitter(0L));

        mvc.perform(post("/api/assistant/sessions/9/messages/44/regenerate/stream")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L).requestAttr("role", "STUDENT")
                        .accept(MediaType.TEXT_EVENT_STREAM))
                .andExpect(status().isOk());

        mvc.perform(get("/api/assistant/runs/8/events/stream")
                        .requestAttr("tenantId", 7L).requestAttr("userId", 21L)
                        .accept(MediaType.TEXT_EVENT_STREAM))
                .andExpect(status().isOk());
    }
}
