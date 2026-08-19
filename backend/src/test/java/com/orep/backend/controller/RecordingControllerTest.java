package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.MeetingRecording;
import com.orep.backend.mapper.MeetingMapper;
import com.orep.backend.mapper.MeetingRecordingMapper;
import com.orep.backend.service.LiveKitEgressService;
import com.orep.backend.service.MinioService;
import com.orep.backend.service.PlaybackLibraryService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class RecordingControllerTest {
    private final MinioService minioService = mock(MinioService.class);
    private final LiveKitEgressService liveKitEgressService = mock(LiveKitEgressService.class);
    private final MeetingRecordingMapper recordingMapper = mock(MeetingRecordingMapper.class);
    private final MeetingMapper meetingMapper = mock(MeetingMapper.class);
    private final PlaybackLibraryService playbackLibraryService = mock(PlaybackLibraryService.class);
    private RecordingController controller;

    @BeforeEach
    void setUp() {
        controller = new RecordingController(
                minioService, liveKitEgressService, recordingMapper, meetingMapper, playbackLibraryService);
    }

    @Test
    void getMyRecordingsAddsLegacyMeetingTitleAndFilePath() {
        List<Map<String, Object>> library = new ArrayList<>();
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("title", "路演A");
        item.put("playUrl", "https://cdn.example/a.webm");
        library.add(item);
        when(playbackLibraryService.listForStudent(9L, 1L)).thenReturn(library);

        Result<List<Map<String, Object>>> result = controller.getMyRecordings(authenticatedRequest());

        assertEquals(200, result.getCode());
        assertEquals("路演A", result.getData().getFirst().get("meetingTitle"));
        assertEquals("https://cdn.example/a.webm", result.getData().getFirst().get("filePath"));
        assertEquals("路演A", result.getData().getFirst().get("title"));
    }

    @Test
    void getMyRecordingsDoesNotOverwriteExistingLegacyFields() {
        List<Map<String, Object>> library = new ArrayList<>();
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("title", "新标题");
        item.put("meetingTitle", "旧标题");
        item.put("playUrl", "https://cdn.example/new.webm");
        item.put("filePath", "already/set.webm");
        library.add(item);
        when(playbackLibraryService.listForStudent(9L, 1L)).thenReturn(library);

        Result<List<Map<String, Object>>> result = controller.getMyRecordings(authenticatedRequest());

        assertEquals("旧标题", result.getData().getFirst().get("meetingTitle"));
        assertEquals("already/set.webm", result.getData().getFirst().get("filePath"));
    }

    @Test
    void getMyRecordingsRequiresLogin() {
        Result<List<Map<String, Object>>> result = controller.getMyRecordings(new MockHttpServletRequest());

        assertEquals(401, result.getCode());
        assertNull(result.getData());
    }

    @Test
    void getMeetingRecordingsRequiresLogin() {
        Result<List<MeetingRecording>> result = controller.getMeetingRecordings(4L, new MockHttpServletRequest());

        assertEquals(401, result.getCode());
        assertNull(result.getData());
    }

    @Test
    void getMeetingRecordingsHidesForeignMeetingAsEmptyList() {
        MeetingRecording foreign = recording(11L, 4L, 99L);
        when(recordingMapper.selectByMeetingId(4L)).thenReturn(List.of(foreign));
        when(recordingMapper.hasMeetingAccess(4L, 1L)).thenReturn(false);

        Result<List<MeetingRecording>> result = controller.getMeetingRecordings(4L, authenticatedRequest());

        assertEquals(200, result.getCode());
        assertTrue(result.getData().isEmpty());
    }

    @Test
    void getMeetingRecordingsReturnsAllRowsForParticipant() {
        MeetingRecording own = recording(11L, 7L, 1L);
        MeetingRecording teammate = recording(12L, 7L, 8L);
        when(recordingMapper.selectByMeetingId(7L)).thenReturn(List.of(own, teammate));
        when(recordingMapper.hasMeetingAccess(7L, 1L)).thenReturn(true);

        Result<List<MeetingRecording>> result = controller.getMeetingRecordings(7L, authenticatedRequest());

        assertEquals(200, result.getCode());
        assertEquals(2, result.getData().size());
        assertEquals(11L, result.getData().get(0).getId());
        assertEquals(12L, result.getData().get(1).getId());
    }

    @Test
    void getMeetingRecordingsReturnsOnlyOwnedRowsWhenNotParticipant() {
        MeetingRecording own = recording(11L, 7L, 1L);
        MeetingRecording other = recording(12L, 7L, 8L);
        when(recordingMapper.selectByMeetingId(7L)).thenReturn(List.of(own, other));
        when(recordingMapper.hasMeetingAccess(7L, 1L)).thenReturn(false);

        Result<List<MeetingRecording>> result = controller.getMeetingRecordings(7L, authenticatedRequest());

        assertEquals(200, result.getCode());
        assertEquals(1, result.getData().size());
        assertEquals(11L, result.getData().getFirst().getId());
    }

    private static MeetingRecording recording(Long id, Long meetingId, Long userId) {
        MeetingRecording recording = new MeetingRecording();
        recording.setId(id);
        recording.setMeetingId(meetingId);
        recording.setUserId(userId);
        return recording;
    }

    private MockHttpServletRequest authenticatedRequest() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setAttribute("userId", 1L);
        request.setAttribute("tenantId", 9L);
        return request;
    }
}
