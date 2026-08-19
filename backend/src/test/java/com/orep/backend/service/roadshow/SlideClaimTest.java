package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SlideClaimTest {

    @Test
    void titleIsClaimNotSpeakerPrefix() {
        String title = SlideClaim.title("team", "项目经理： 我是本项目的项目经理兼溯源工程师，主要负责团队任务安排。");
        assertEquals("岗位分工", title);
        assertFalse(title.startsWith("项目经理"));
    }

    @Test
    void openingUsesBookTitle() {
        String title = SlideClaim.title("hook",
                "逐字稿全文 项目经理： 尊敬的各位专家评委，大家好！ 全体成员： 《慧眼识\"株\"，智培鲜果》");
        assertTrue(title.contains("慧眼") || title.equals("开场"));
        assertFalse(title.contains("逐字稿"));
        assertFalse(title.startsWith("项目经理"));
    }

    @Test
    void policyDocIsNotSlideTitle() {
        String title = SlideClaim.title("hook", "河南省规划对齐《加快建设农业强国规划（2024—2035年）》");
        assertEquals("政策背景", title);
    }

    @Test
    void methodKeepsSoilVisionPhrase() {
        assertEquals("识土、识图、使谱",
                SlideClaim.title("method", "项目经理： 我们系统的总体思路是通过\"识土、识图、使谱\"，实现智能化。"));
    }
}
