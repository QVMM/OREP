package com.orep.backend.controller;

import com.orep.backend.service.ProjectPreparationService;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class ProjectPreparationControllerTest {

    @Test
    void bootstrapDelegatesWithTenantUserRoleAndTeamId() throws Exception {
        ProjectPreparationService service = mock(ProjectPreparationService.class);
        when(service.bootstrap(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of("activeTeamId", 9L, "prepSession", Map.of("id", 88L)));
        MockMvc mvc = standaloneSetup(new ProjectPreparationController(service)).build();

        mvc.perform(get("/api/project-prep/bootstrap")
                        .param("teamId", "9")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.activeTeamId").value(9))
                .andExpect(jsonPath("$.data.prepSession.id").value(88));

        verify(service).bootstrap(9L, 3L, 12L, "STUDENT");
    }

    @Test
    void sendMessageDelegatesBodyAndRequestAttributes() throws Exception {
        ProjectPreparationService service = mock(ProjectPreparationService.class);
        when(service.sendMessage(eq(88L), eq(Map.of("content", "我们有温室传感器数据")), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of("accepted", true, "message", "已生成选题策划建议"));
        MockMvc mvc = standaloneSetup(new ProjectPreparationController(service)).build();

        mvc.perform(post("/api/project-prep/sessions/88/messages")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "STUDENT")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"content\":\"我们有温室传感器数据\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.accepted").value(true))
                .andExpect(jsonPath("$.data.message").value("已生成选题策划建议"));

        verify(service).sendMessage(88L, Map.of("content", "我们有温室传感器数据"), 3L, 12L, "STUDENT");
    }
}
