package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.TrackRubricConfig;
import com.orep.backend.mapper.TrackRubricConfigMapper;
import org.springframework.stereotype.Service;

@Service
public class TrackRubricConfigService {
    private final TrackRubricConfigMapper mapper;

    public TrackRubricConfigService(TrackRubricConfigMapper mapper) {
        this.mapper = mapper;
    }

    public TrackRubricConfig resolveActive(String trackId, String trackName) {
        LambdaQueryWrapper<TrackRubricConfig> wrapper = new LambdaQueryWrapper<TrackRubricConfig>()
                .eq(TrackRubricConfig::getStatus, "active")
                .eq(TrackRubricConfig::getActiveSlot, "ACTIVE")
                .last("LIMIT 1");
        if (trackId != null && !trackId.isBlank()) {
            wrapper.eq(TrackRubricConfig::getTrackId, trackId);
        } else if (trackName != null && !trackName.isBlank()) {
            wrapper.eq(TrackRubricConfig::getTrackName, trackName);
        } else {
            throw new IllegalArgumentException("trackId 或 trackName 不能为空");
        }

        TrackRubricConfig active = mapper.selectOne(wrapper);
        if (active == null) {
            throw new IllegalStateException("该赛道评分标准尚未配置，请联系管理员");
        }
        return active;
    }
}
