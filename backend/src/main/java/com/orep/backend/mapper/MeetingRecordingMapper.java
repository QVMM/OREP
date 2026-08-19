package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.MeetingRecording;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface MeetingRecordingMapper extends BaseMapper<MeetingRecording> {

    /**
     * 查询某用户相关的所有录制（参与者 或 创建者 或 上传者）
     */
    @Select("SELECT DISTINCT r.* FROM meeting_recording r " +
            "LEFT JOIN meeting_participant mp ON mp.meeting_id = r.meeting_id AND mp.user_id = #{userId} " +
            "LEFT JOIN meeting m ON m.id = r.meeting_id " +
            "WHERE mp.user_id = #{userId} OR m.creator_id = #{userId} OR r.user_id = #{userId} " +
            "ORDER BY r.recorded_at DESC")
    List<MeetingRecording> selectByParticipantUserId(@Param("userId") Long userId);

    /**
     * 查询某个会议的所有录制
     */
    @Select("SELECT * FROM meeting_recording WHERE meeting_id = #{meetingId} ORDER BY recorded_at DESC")
    List<MeetingRecording> selectByMeetingId(@Param("meetingId") Long meetingId);

    @Select("SELECT * FROM meeting_recording " +
            "WHERE meeting_id = #{meetingId} AND status IN ('STARTING','RECORDING','PROCESSING') " +
            "ORDER BY id DESC LIMIT 1")
    MeetingRecording selectActiveByMeetingId(@Param("meetingId") Long meetingId);

    @Select("SELECT COUNT(1) > 0 FROM meeting m " +
            "LEFT JOIN meeting_participant mp ON mp.meeting_id = m.id AND mp.user_id = #{userId} " +
            "WHERE m.id = #{meetingId} AND (m.creator_id = #{userId} OR mp.user_id = #{userId})")
    boolean hasMeetingAccess(@Param("meetingId") Long meetingId, @Param("userId") Long userId);
}
