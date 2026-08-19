package com.orep.backend.controller;

import com.orep.backend.service.NotificationService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class NotificationControllerTest {

    @Test
    void listUsesAuthenticatedTenantAndUser() throws Exception {
        NotificationService service = mock(NotificationService.class);
        when(service.notifications(7L, 21L)).thenReturn(Map.of(
                "unreadCount", 1,
                "items", List.of(Map.of("id", 9L, "title", "集训任务提醒"))
        ));
        MockMvc mvc = standaloneSetup(new NotificationController(service)).build();

        mvc.perform(get("/api/notifications")
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unreadCount").value(1))
                .andExpect(jsonPath("$.data.items[0].id").value(9));

        verify(service).notifications(7L, 21L);
    }

    @Test
    void markReadUsesAuthenticatedTenantAndUser() throws Exception {
        NotificationService service = mock(NotificationService.class);
        when(service.markRead(7L, 21L, 9L)).thenReturn(Map.of("id", 9L, "isRead", true));
        MockMvc mvc = standaloneSetup(new NotificationController(service)).build();

        mvc.perform(patch("/api/notifications/9/read")
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.id").value(9))
                .andExpect(jsonPath("$.data.isRead").value(true));

        verify(service).markRead(7L, 21L, 9L);
    }

    @Test
    void markAllReadUsesAuthenticatedTenantAndUser() throws Exception {
        NotificationService service = mock(NotificationService.class);
        when(service.markAllRead(7L, 21L)).thenReturn(Map.of("unreadCount", 0, "updatedCount", 3));
        MockMvc mvc = standaloneSetup(new NotificationController(service)).build();

        mvc.perform(patch("/api/notifications/read-all")
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.unreadCount").value(0))
                .andExpect(jsonPath("$.data.updatedCount").value(3));

        verify(service).markAllRead(7L, 21L);
    }
}
