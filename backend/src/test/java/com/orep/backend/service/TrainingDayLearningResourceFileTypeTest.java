package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;

class TrainingDayLearningResourceFileTypeTest {
    private TrainingDayLearningResourceService service;

    @TempDir
    Path uploadRoot;

    @BeforeEach
    void setUp() {
        service = new TrainingDayLearningResourceService(
                mock(JdbcTemplate.class),
                new ObjectMapper(),
                uploadRoot.toString(),
                new TrainingDayAvailabilityService()
        );
    }

    @Test
    void classifiesEverySupportedLearningFileWithoutChangingDatabaseResourceTypes() {
        List<String> videos = List.of("mp4", "webm", "mov");
        List<String> documents = List.of(
                "mp3", "wav", "m4a",
                "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
                "csv", "txt", "md",
                "jpg", "jpeg", "png", "gif", "webp",
                "zip", "rar", "7z"
        );

        videos.forEach(extension -> assertEquals("VIDEO", service.classifyResourceType(extension), extension));
        documents.forEach(extension -> assertEquals("DOCUMENT", service.classifyResourceType(extension), extension));
        assertNull(service.classifyResourceType("exe"));
        assertNull(service.classifyResourceType("svg"));
    }

    @Test
    void derivesSafeMimeTypesFromVerifiedExtensions() {
        Map<String, String> expected = Map.ofEntries(
                Map.entry("mp3", "audio/mpeg"),
                Map.entry("m4a", "audio/mp4"),
                Map.entry("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                Map.entry("xls", "application/vnd.ms-excel"),
                Map.entry("csv", "text/csv"),
                Map.entry("md", "text/markdown"),
                Map.entry("jpg", "image/jpeg"),
                Map.entry("zip", "application/zip"),
                Map.entry("rar", "application/vnd.rar"),
                Map.entry("7z", "application/x-7z-compressed")
        );

        expected.forEach((extension, mime) -> assertEquals(mime, service.safeMime(extension), extension));
    }

    @Test
    void acceptsRepresentativeHeadersFromEveryNewFileCategory() throws Exception {
        Map<String, byte[]> files = Map.ofEntries(
                Map.entry("mp3", bytes("ID3demo")),
                Map.entry("wav", bytes("RIFF0000WAVE")),
                Map.entry("m4a", bytes("\u0000\u0000\u0000\u0018ftypM4A ")),
                Map.entry("xls", new byte[] {
                        (byte) 0xd0, (byte) 0xcf, 0x11, (byte) 0xe0,
                        (byte) 0xa1, (byte) 0xb1, 0x1a, (byte) 0xe1
                }),
                Map.entry("csv", bytes("姓名,成绩\n学生甲,95\n")),
                Map.entry("txt", bytes("训练说明")),
                Map.entry("md", bytes("# 今日学习")),
                Map.entry("jpg", new byte[] {(byte) 0xff, (byte) 0xd8, (byte) 0xff, 0x00}),
                Map.entry("png", new byte[] {(byte) 0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a}),
                Map.entry("gif", bytes("GIF89a")),
                Map.entry("webp", bytes("RIFF0000WEBP")),
                Map.entry("zip", zipEntries("materials/readme.txt")),
                Map.entry("rar", new byte[] {'R', 'a', 'r', '!', 0x1a, 0x07, 0x00}),
                Map.entry("7z", new byte[] {0x37, 0x7a, (byte) 0xbc, (byte) 0xaf, 0x27, 0x1c})
        );

        files.forEach((extension, content) -> assertDoesNotThrow(
                () -> service.validateFileSignature(file(extension, content), extension),
                extension
        ));
    }

    @Test
    void distinguishesDocxPptxAndXlsxFromOrdinaryZipContainers() throws Exception {
        assertDoesNotThrow(() -> service.validateFileSignature(
                file("docx", zipEntries("[Content_Types].xml", "word/document.xml")),
                "docx"
        ));
        assertDoesNotThrow(() -> service.validateFileSignature(
                file("pptx", zipEntries("[Content_Types].xml", "ppt/presentation.xml")),
                "pptx"
        ));
        assertDoesNotThrow(() -> service.validateFileSignature(
                file("xlsx", zipEntries("[Content_Types].xml", "xl/workbook.xml")),
                "xlsx"
        ));

        assertThrows(ResponseStatusException.class, () -> service.validateFileSignature(
                file("xlsx", zipEntries("[Content_Types].xml", "word/document.xml")),
                "xlsx"
        ));
        assertThrows(ResponseStatusException.class, () -> service.validateFileSignature(
                file("xlsx", zipEntries("materials/readme.txt")),
                "xlsx"
        ));
    }

    @Test
    void rejectsBinaryContentMasqueradingAsText() {
        assertThrows(ResponseStatusException.class, () -> service.validateFileSignature(
                file("csv", new byte[] {'a', ',', 'b', 0x00, 0x01}),
                "csv"
        ));
    }

    private MockMultipartFile file(String extension, byte[] content) {
        return new MockMultipartFile(
                "file",
                "learning." + extension,
                "application/octet-stream",
                content
        );
    }

    private byte[] zipEntries(String... names) throws Exception {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(output)) {
            for (String name : names) {
                zip.putNextEntry(new ZipEntry(name));
                zip.write(new byte[] {1});
                zip.closeEntry();
            }
        }
        return output.toByteArray();
    }

    private byte[] bytes(String value) {
        return value.getBytes(StandardCharsets.UTF_8);
    }
}
