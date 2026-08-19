package com.orep.backend.controller;

import com.orep.backend.service.ResourceCenterService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class ResourceCenterControllerTest {

    @Test
    void workspaceUsesAuthenticatedScope() throws Exception {
        ResourceCenterService service = mock(ResourceCenterService.class);
        when(service.workspace(3L, 7L, 21L, "STUDENT")).thenReturn(Map.of(
                "teamId", 3L,
                "folders", List.of(Map.of("key", "team", "label", "团队项目材料"))
        ));
        MockMvc mvc = standaloneSetup(new ResourceCenterController(service)).build();

        mvc.perform(get("/api/resource-center")
                        .param("teamId", "3")
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.teamId").value(3))
                .andExpect(jsonPath("$.data.folders[0].key").value("team"));

        verify(service).workspace(3L, 7L, 21L, "STUDENT");
    }

    @Test
    void moveIgnoresActorFieldsFromRequestBody() throws Exception {
        ResourceCenterService service = mock(ResourceCenterService.class);
        when(service.moveFile(
                eq(14), eq(3L), eq(7L), eq(21L), eq("STUDENT"), anyString()
        )).thenReturn(Map.of("id", 14, "folderKey", "content"));
        MockMvc mvc = standaloneSetup(new ResourceCenterController(service)).build();

        mvc.perform(patch("/api/resource-center/files/14/folder")
                        .contentType("application/json")
                        .content("""
                            {"teamId":3,"folderKey":"content","userId":999,"tenantId":999}
                            """)
                        .requestAttr("tenantId", 7L)
                        .requestAttr("userId", 21L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.folderKey").value("content"));

        verify(service).moveFile(14, 3L, 7L, 21L, "STUDENT", "content");
    }
}
