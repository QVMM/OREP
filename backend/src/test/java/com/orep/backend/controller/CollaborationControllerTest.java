package com.orep.backend.controller;

import com.orep.backend.service.CollaborationService;
import com.orep.backend.service.CollaborationWorkItemService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class CollaborationControllerTest {

    @Test
    void summaryAndItemsUseAuthenticatedScope() throws Exception {
        CollaborationService service = mock(CollaborationService.class);
        CollaborationWorkItemService workItems = mock(CollaborationWorkItemService.class);
        when(workItems.summary(7L, 21L, "STUDENT")).thenReturn(Map.of("actionRequired", 2));
        when(workItems.items(7L, 21L, "STUDENT", "ALL", 8L, null, 30))
                .thenReturn(Map.of("items", List.of(Map.of("id", 9L)), "hasMore", false));
        MockMvc mvc = standaloneSetup(new CollaborationController(service, workItems, true)).build();

        mvc.perform(get("/api/collaboration/summary")
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.actionRequired").value(2));

        mvc.perform(get("/api/collaboration/items")
                        .param("view", "ALL")
                        .param("teamId", "8")
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].id").value(9));
    }

    @Test
    void createPassesIdempotencyHeaderWithoutAcceptingActorFromBody() throws Exception {
        CollaborationService service = mock(CollaborationService.class);
        CollaborationWorkItemService workItems = mock(CollaborationWorkItemService.class);
        when(service.createRequest(
                org.mockito.ArgumentMatchers.eq(7L),
                org.mockito.ArgumentMatchers.eq(21L),
                org.mockito.ArgumentMatchers.eq("STUDENT"),
                org.mockito.ArgumentMatchers.eq("create-42"),
                anyMap()
        )).thenReturn(Map.of("id", 42L, "status", "PENDING"));
        MockMvc mvc = standaloneSetup(new CollaborationController(service, workItems, true)).build();

        mvc.perform(post("/api/collaboration/requests")
                        .header("Idempotency-Key", "create-42")
                        .contentType("application/json")
                        .content("""
                            {"teamId":8,"recipientUserId":22,"title":"完善路演稿",
                             "tenantId":999,"requesterId":999}
                            """)
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(42));

        verify(service).createRequest(
                org.mockito.ArgumentMatchers.eq(7L),
                org.mockito.ArgumentMatchers.eq(21L),
                org.mockito.ArgumentMatchers.eq("STUDENT"),
                org.mockito.ArgumentMatchers.eq("create-42"),
                anyMap()
        );
    }

    @Test
    void batchCreateUsesAuthenticatedScopeAndBatchIdempotencyHeader() throws Exception {
        CollaborationService service = mock(CollaborationService.class);
        CollaborationWorkItemService workItems = mock(CollaborationWorkItemService.class);
        when(service.createRequests(
                org.mockito.ArgumentMatchers.eq(7L),
                org.mockito.ArgumentMatchers.eq(21L),
                org.mockito.ArgumentMatchers.eq("STUDENT"),
                org.mockito.ArgumentMatchers.eq("batch-42"),
                anyMap()
        )).thenReturn(Map.of(
                "count", 2,
                "items", List.of(Map.of("id", 42L), Map.of("id", 43L))
        ));
        MockMvc mvc = standaloneSetup(new CollaborationController(service, workItems, true)).build();

        mvc.perform(post("/api/collaboration/requests/batch")
                        .header("Idempotency-Key", "batch-42")
                        .contentType("application/json")
                        .content("""
                            {"teamId":8,"recipientUserIds":[22,23],"title":"完善路演稿",
                             "tenantId":999,"requesterId":999}
                            """)
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.count").value(2))
                .andExpect(jsonPath("$.data.items[1].id").value(43));

        verify(service).createRequests(
                org.mockito.ArgumentMatchers.eq(7L),
                org.mockito.ArgumentMatchers.eq(21L),
                org.mockito.ArgumentMatchers.eq("STUDENT"),
                org.mockito.ArgumentMatchers.eq("batch-42"),
                anyMap()
        );
    }

    @Test
    void disabledFeatureDoesNotExposeEndpoints() throws Exception {
        CollaborationService service = mock(CollaborationService.class);
        CollaborationWorkItemService workItems = mock(CollaborationWorkItemService.class);
        MockMvc mvc = standaloneSetup(new CollaborationController(service, workItems, false))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();

        mvc.perform(get("/api/collaboration/summary")
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(404));
    }
}
