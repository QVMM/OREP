package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.TrackRubricConfig;
import com.orep.backend.mapper.TrackRubricConfigMapper;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class TrackRubricConfigServiceTest {

    @Test
    void resolvesActiveRubricForTrack() {
        TrackRubricConfigMapper mapper = mock(TrackRubricConfigMapper.class);
        TrackRubricConfig active = new TrackRubricConfig();
        active.setTrackId("track-it");
        active.setTrackName("新一代信息技术赛道");
        active.setRubricId("rubric-it-v1");
        active.setInternalVersion("v1.2-internal");
        active.setRubricHash("secret-hash");
        active.setRubricPath("/secret/rubric.md");
        active.setStatus("active");
        active.setActiveSlot("ACTIVE");
        when(mapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(active);

        TrackRubricConfigService service = new TrackRubricConfigService(mapper);

        TrackRubricConfig resolved = service.resolveActive("track-it", null);

        assertEquals("rubric-it-v1", resolved.getRubricId());
        assertEquals("ACTIVE", resolved.getActiveSlot());
    }

    @Test
    void failsWhenNoActiveRubricExists() {
        TrackRubricConfigMapper mapper = mock(TrackRubricConfigMapper.class);
        when(mapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);

        TrackRubricConfigService service = new TrackRubricConfigService(mapper);

        IllegalStateException error = assertThrows(IllegalStateException.class,
                () -> service.resolveActive("track-missing", "未知赛道"));
        assertTrue(error.getMessage().contains("评分标准尚未配置"));
    }
}
