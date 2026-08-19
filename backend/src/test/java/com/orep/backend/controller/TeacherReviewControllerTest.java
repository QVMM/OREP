package com.orep.backend.controller;

import com.orep.backend.service.ProjectTeamService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Map;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class TeacherReviewControllerTest {

    @Test
    void reviewQueueDelegatesWithTenantUserAndRoleAttributes() throws Exception {
        ProjectTeamService service = mock(ProjectTeamService.class);
        when(service.teacherReviewQueue(3L, 12L, "TEACHER"))
                .thenReturn(List.of(Map.of("submissionId", 101L, "taskTitle", "完善商业计划书")));
        MockMvc mvc = standaloneSetup(new TeacherReviewController(service)).build();

        mvc.perform(get("/api/teacher/review-queue")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "TEACHER"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data[0].submissionId").value(101))
                .andExpect(jsonPath("$.data[0].taskTitle").value("完善商业计划书"));

        verify(service).teacherReviewQueue(3L, 12L, "TEACHER");
    }

    @Test
    void submissionDetailDelegatesWithSubmissionTenantUserAndRole() throws Exception {
        ProjectTeamService service = mock(ProjectTeamService.class);
        when(service.teacherSubmissionDetail(101L, 3L, 12L, "TEACHER"))
                .thenReturn(Map.of("submissionId", 101L, "canReview", true));
        MockMvc mvc = standaloneSetup(new TeacherReviewController(service)).build();

        mvc.perform(get("/api/teacher/submissions/101")
                        .requestAttr("tenantId", 3L)
                        .requestAttr("userId", 12L)
                        .requestAttr("role", "TEACHER"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.submissionId").value(101))
                .andExpect(jsonPath("$.data.canReview").value(true));

        verify(service).teacherSubmissionDetail(101L, 3L, 12L, "TEACHER");
    }
}
