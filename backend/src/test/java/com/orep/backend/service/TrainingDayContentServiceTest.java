package com.orep.backend.service;

import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import java.io.ByteArrayOutputStream;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;

class TrainingDayContentServiceTest {

    @Test
    void partialTeacherCannotWriteSharedTrainingDayContent() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class)))
                .thenReturn(1);
        when(jdbc.queryForList(anyString(), eq(Long.class), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            return sql.contains("FROM training_camp_team")
                    ? List.of(101L, 102L)
                    : List.of(101L);
        });
        when(jdbc.queryForList(
                org.mockito.ArgumentMatchers.contains("FROM training_day d"),
                any(Object[].class)
        )).thenReturn(List.of(Map.of("campId", 31L)));
        TrainingDayContentService service =
                new TrainingDayContentService(jdbc, "./target/test-uploads");
        MockMultipartFile invalidImage = new MockMultipartFile(
                "file", "image.png", "image/png", "not an image".getBytes()
        );

        ResponseStatusException error = assertThrows(
                ResponseStatusException.class,
                () -> service.uploadContentImage(
                        7L,
                        88L,
                        "TEACHER",
                        51L,
                        invalidImage
                )
        );

        assertEquals(HttpStatus.FORBIDDEN, error.getStatusCode());
    }

    @Test
    void partialTeacherCanStillReadAttachmentMetadataForOwnTeamScope() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(anyString(), eq(Integer.class), any(Object[].class)))
                .thenReturn(1);

        TrainingDayContentService service =
                new TrainingDayContentService(jdbc, "./target/test-uploads");

        assertDoesNotThrow(() ->
                service.teacherAttachments(7L, 88L, "TEACHER", 51L)
        );
    }

    @Test
    void richTextSanitizerKeepsSupportedContentAndRejectsUnsafeMedia() {
        TrainingDayContentService service = new TrainingDayContentService(mock(JdbcTemplate.class), "./target/test-uploads");

        String clean = service.sanitizeHtml("""
            <h1>一级标题</h1>
            <h2 onclick="alert(1)">任务背景</h2>
            <p><strong>重点</strong><span style="color: rgb(232, 74, 28); font-size: 99px">主题色</span><script>alert(1)</script></p>
            <p><span style="color: blue; position: fixed">非法颜色</span></p>
            <img src="https://evil.example/track.png" onerror="alert(1)">
            <img src="/uploads/task/instructions/22/images/safe.jpg?t=secret" alt="示意图">
            <a href="javascript:alert(1)">坏链接</a>
            <a href="https://example.com/guide">参考资料</a>
            """);

        assertTrue(clean.contains("<h1>一级标题</h1>"));
        assertTrue(clean.contains("<h2>任务背景</h2>"));
        assertTrue(clean.contains("data-text-color=\"orange\""));
        assertTrue(clean.contains("style=\"color: #e84a1c\""));
        assertTrue(clean.contains("非法颜色"));
        assertFalse(clean.contains("color: blue"));
        assertFalse(clean.contains("font-size"));
        assertFalse(clean.contains("position"));
        assertTrue(clean.contains("/uploads/task/instructions/22/images/safe.jpg"));
        assertFalse(clean.contains("t=secret"));
        assertTrue(clean.contains("noopener noreferrer"));
        assertFalse(clean.contains("script"));
        assertFalse(clean.contains("onclick"));
        assertFalse(clean.contains("evil.example"));
        assertFalse(clean.contains("javascript:"));
    }

    @Test
    void attachmentValidationRejectsRenamedFiles() {
        TrainingDayContentService service = new TrainingDayContentService(mock(JdbcTemplate.class), "./target/test-uploads");
        MockMultipartFile fakePdf = new MockMultipartFile(
                "file", "伪装文件.pdf", "application/pdf", "not a pdf".getBytes()
        );

        assertThrows(ResponseStatusException.class, () ->
                ReflectionTestUtils.invokeMethod(service, "validateAttachmentContent", fakePdf, "pdf")
        );
    }

    @Test
    void attachmentValidationAcceptsARealDocxPackage() throws Exception {
        TrainingDayContentService service = new TrainingDayContentService(mock(JdbcTemplate.class), "./target/test-uploads");
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(bytes)) {
            zip.putNextEntry(new ZipEntry("[Content_Types].xml"));
            zip.write("<Types/>".getBytes());
            zip.closeEntry();
            zip.putNextEntry(new ZipEntry("word/document.xml"));
            zip.write("<document/>".getBytes());
            zip.closeEntry();
        }
        MockMultipartFile docx = new MockMultipartFile(
                "file", "任务模板.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", bytes.toByteArray()
        );

        assertDoesNotThrow(() ->
                ReflectionTestUtils.invokeMethod(service, "validateAttachmentContent", docx, "docx")
        );
    }
}
