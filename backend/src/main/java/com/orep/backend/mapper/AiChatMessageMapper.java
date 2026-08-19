package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.AiChatMessage;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface AiChatMessageMapper extends BaseMapper<AiChatMessage> {
}
