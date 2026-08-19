package com.orep.backend.controller;

import com.orep.backend.service.ProjectTeamService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Map;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class ProjectTeamControllerTest {

    @Test
    void taskDetailReturnsCompleteTaskBookForCurrentTeam() throws Exception {
        ProjectTeamService service = mock(ProjectTeamService.class);
        when(service.taskDetail(eq(9L), eq(36L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "task", Map.of("id", 36L, "title", "确定项目问题与用户需求"),
                        "taskBook", Map.of(
                                "contentHtml", "<p>完成用户访谈并整理证据。</p>",
                                "requirements", java.util.List.of(Map.of("id", 1L, "title", "访谈记录")),
                                "attachments", java.util.List.of(Map.of("id", 2L, "fileName", "访谈模板.pdf"))
                        )
                ));
        MockMvc mvc = standaloneSetup(new ProjectTeamController(service)).build();

        mvc.perform(get("/api/project-teams/9/tasks/36")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.task.id").value(36))
                .andExpect(jsonPath("$.data.taskBook.requirements[0].title").value("访谈记录"))
                .andExpect(jsonPath("$.data.taskBook.attachments[0].fileName").value("访谈模板.pdf"));

        verify(service).taskDetail(9L, 36L, 3L, 12L, "STUDENT");
    }

    @Test
    void dashboardReturnsDynamicCompetitionReadinessPayload() throws Exception {
        ProjectTeamService service = mock(ProjectTeamService.class);
        when(service.dashboard(eq(9L), eq(3L), eq(12L), eq("STUDENT")))
                .thenReturn(Map.of(
                        "team", Map.of("id", 9L, "name", "智慧养老项目"),
                        "competitionReadiness", Map.of(
                                "activity", Map.of("total", 7),
                                "gaps", java.util.List.of(Map.of("key", "roadshow", "title", "完成一次计时路演并生成评分"))
                        )
                ));
        MockMvc mvc = standaloneSetup(new ProjectTeamController(service)).build();

        mvc.perform(get("/api/project-teams/9/dashboard")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.competitionReadiness.activity.total").value(7))
                .andExpect(jsonPath("$.data.competitionReadiness.gaps[0].key").value("roadshow"));

        verify(service).dashboard(9L, 3L, 12L, "STUDENT");
    }

    @Test
    void roadshowMemoryEndpointDelegatesWithTenantUserAndRoleAttributes() throws Exception {
        ProjectTeamService service = mock(ProjectTeamService.class);
        when(service.roadshowMemory(eq(9L), eq(3L), eq(12L), eq("TEACHER")))
                .thenReturn(Map.of(
                        "teamId", 9L,
                        "memoryStatus", "SINGLE_ROUND",
                        "memoryStatusText", "已完成1轮AI评分，下一轮评分后会自动复检本轮扣分项。"
                ));
        MockMvc mvc = standaloneSetup(new ProjectTeamController(service)).build();

        mvc.perform(get("/api/project-teams/9/roadshow-memory")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "TEACHER"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.teamId").value(9))
                .andExpect(jsonPath("$.data.memoryStatus").value("SINGLE_ROUND"));

        verify(service).roadshowMemory(9L, 3L, 12L, "TEACHER");
    }

    @Test
    void evidenceExcerptEndpointDelegatesWithTenantUserAndRoleAttributes() throws Exception {
        ProjectTeamService service = mock(ProjectTeamService.class);
        when(service.evidenceExcerpt(eq(9L), eq(1001L), eq("frame-001@00:31.5"), eq(3L), eq(12L), eq("TEACHER")))
                .thenReturn(Map.of(
                        "teamId", 9L,
                        "aiReportId", 1001L,
                        "type", "key_frame",
                        "summary", "屏幕展示登录成功和数据看板"
                ));
        MockMvc mvc = standaloneSetup(new ProjectTeamController(service)).build();

        mvc.perform(get("/api/project-teams/9/evidence-excerpt")
                        .param("aiReportId", "1001")
                        .param("sourceRef", "frame-001@00:31.5")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "TEACHER"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.teamId").value(9))
                .andExpect(jsonPath("$.data.type").value("key_frame"))
                .andExpect(jsonPath("$.data.summary").value("屏幕展示登录成功和数据看板"));

        verify(service).evidenceExcerpt(9L, 1001L, "frame-001@00:31.5", 3L, 12L, "TEACHER");
    }

    @Test
    void roadshowRosterRequiresViewerAndDoesNotCallInternalDump() throws Exception {
        ProjectTeamService service = mock(ProjectTeamService.class);
        when(service.roadshowTeamRoster(eq(13L), eq(3L), eq(11L), eq("STUDENT")))
                .thenReturn(java.util.List.of());
        MockMvc mvc = standaloneSetup(new ProjectTeamController(service)).build();

        mvc.perform(get("/api/project-teams/roadshow-roster/13")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 11L)
                        .requestAttr("role", "STUDENT"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").isEmpty());

        verify(service).roadshowTeamRoster(13L, 3L, 11L, "STUDENT");
        verify(service, org.mockito.Mockito.never()).roadshowTeamRoster(13L);
    }
}
