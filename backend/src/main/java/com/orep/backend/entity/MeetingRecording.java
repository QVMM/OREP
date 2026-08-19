package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("meeting_recording")
public class MeetingRecording {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long meetingId;
    private Long userId;
    private String recordingId;
    private String status;          // STARTING | RECORDING | PROCESSING | READY | FAILED
    private String filePath;        // 主录制视频，必须包含音频轨
    private String mimeType;
    private Long sizeBytes;
    private Boolean hasAudio;
    private Boolean hasVideo;
    private String errorMessage;
    private String cameraFile;      // MinIO 对象路径，可为 null
    private String screenFile;      // MinIO 对象路径，可为 null
    private String audioFile;       // MinIO 对象路径
    private Long audioSizeBytes;
    private Integer durationSeconds;
    private String meetingTitle;     // 冗余存储，方便列表展示
    private LocalDateTime startedAt;
    private LocalDateTime endedAt;
    private LocalDateTime recordedAt;
}
