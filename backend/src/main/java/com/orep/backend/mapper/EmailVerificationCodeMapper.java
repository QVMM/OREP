package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.EmailVerificationCode;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface EmailVerificationCodeMapper extends BaseMapper<EmailVerificationCode> {}
