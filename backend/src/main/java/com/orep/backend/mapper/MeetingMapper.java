package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.Meeting;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface MeetingMapper extends BaseMapper<Meeting> {}
