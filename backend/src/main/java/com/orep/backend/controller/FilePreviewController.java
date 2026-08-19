package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.AiScoreUploadAccessService;
import com.orep.backend.service.AssistantUploadAccessService;
import com.orep.backend.service.ChatUploadAccessService;
import com.orep.backend.service.CourseMaterialUploadAccessService;
import com.orep.backend.service.DocumentStoreUploadAccessService;
import com.orep.backend.service.PptTemplateUploadAccessService;
import com.orep.backend.service.TaskInstructionUploadAccessService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.InputSource;

import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.StringReader;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

@RestController
@RequestMapping("/api/file-preview")
public class FilePreviewController {

    private static final int MAX_TEXT_CHARS = 16000;
    private static final long MAX_PREVIEW_BYTES = 8L * 1024L * 1024L;

    @Value("${file.upload-dir:./uploads}")
    private String uploadDir;

    @Autowired(required = false)
    private ChatUploadAccessService chatUploadAccessService;

    @Autowired(required = false)
    private AiScoreUploadAccessService aiScoreUploadAccessService;

    @Autowired(required = false)
    private AssistantUploadAccessService assistantUploadAccessService;

    @Autowired(required = false)
    private DocumentStoreUploadAccessService documentStoreUploadAccessService;

    @Autowired(required = false)
    private CourseMaterialUploadAccessService courseMaterialUploadAccessService;

    @Autowired(required = false)
    private PptTemplateUploadAccessService pptTemplateUploadAccessService;

    @Autowired(required = false)
    private TaskInstructionUploadAccessService taskInstructionUploadAccessService;

    @GetMapping
    public Result<Map<String, Object>> preview(@RequestParam("url") String url,
                                               HttpServletRequest request) {
        try {
            if (chatUploadAccessService != null && chatUploadAccessService.isProtectedChatUpload(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                chatUploadAccessService.authorize(url, userId);
            }
            if (aiScoreUploadAccessService != null && aiScoreUploadAccessService.isProtectedAiScoreUpload(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                Long tenantId = request == null ? null : (request.getAttribute("tenantId") instanceof Number n ? n.longValue() : null);
                Object roleAttr = request == null ? null : request.getAttribute("role");
                String role = roleAttr == null ? null : String.valueOf(roleAttr);
                aiScoreUploadAccessService.authorize(url, tenantId, userId, role);
            }
            if (assistantUploadAccessService != null && assistantUploadAccessService.isProtectedAssistantUpload(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                Long tenantId = request == null ? null : (request.getAttribute("tenantId") instanceof Number n ? n.longValue() : null);
                assistantUploadAccessService.authorize(url, tenantId, userId);
            }
            if (documentStoreUploadAccessService != null && documentStoreUploadAccessService.isProtectedResourceCenterUpload(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                Long tenantId = request == null ? null : (request.getAttribute("tenantId") instanceof Number n ? n.longValue() : null);
                Object roleAttr = request == null ? null : request.getAttribute("role");
                String role = roleAttr == null ? null : String.valueOf(roleAttr);
                documentStoreUploadAccessService.authorizeResourceCenter(url, tenantId, userId, role);
            }
            if (documentStoreUploadAccessService != null && documentStoreUploadAccessService.isProtectedOfficeVersionUpload(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                documentStoreUploadAccessService.authorizeOfficeVersion(url, userId);
            }
            if (courseMaterialUploadAccessService != null && courseMaterialUploadAccessService.isProtectedCourseMaterial(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                Object roleAttr = request == null ? null : request.getAttribute("role");
                String role = roleAttr == null ? null : String.valueOf(roleAttr);
                courseMaterialUploadAccessService.authorize(url, userId, role);
            }
            if (pptTemplateUploadAccessService != null && pptTemplateUploadAccessService.isProtectedPptTemplate(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                pptTemplateUploadAccessService.authorize(url, userId);
            }
            if (taskInstructionUploadAccessService != null && taskInstructionUploadAccessService.isProtectedTaskInstruction(url)) {
                Long userId = request == null ? null : (Long) request.getAttribute("userId");
                Long tenantId = request == null ? null : (request.getAttribute("tenantId") instanceof Number n ? n.longValue() : null);
                Object roleAttr = request == null ? null : request.getAttribute("role");
                String role = roleAttr == null ? null : String.valueOf(roleAttr);
                taskInstructionUploadAccessService.authorize(url, tenantId, userId, role);
            }
            Path file = resolveUploadedFile(url);
            if (!Files.exists(file) || !Files.isRegularFile(file)) {
                return Result.error(404, "文件不存在");
            }
            if (Files.size(file) > MAX_PREVIEW_BYTES) {
                return Result.error(413, "文件超过在线预览大小限制，请下载后查看");
            }

            String fileName = file.getFileName().toString();
            String ext = extensionOf(fileName);
            Map<String, Object> data = new HashMap<>();
            data.put("name", fileName);
            data.put("extension", ext);

            if ("docx".equals(ext)) {
                PreviewText preview = extractDocxText(file);
                data.put("kind", "docx_text");
                data.put("text", preview.text);
                data.put("truncated", preview.truncated);
                data.put("source", "server-docx-text");
                return Result.success(data);
            }

            if (isPlainText(ext)) {
                PreviewText preview = readPlainText(file);
                data.put("kind", "plain_text");
                data.put("text", preview.text);
                data.put("truncated", preview.truncated);
                data.put("source", "server-plain-text");
                return Result.success(data);
            }

            return Result.error(415, "此文件类型暂不支持文本预览");
        } catch (ResponseStatusException e) {
            return Result.error(e.getStatusCode().value(), e.getReason());
        } catch (IllegalArgumentException e) {
            return Result.error(400, e.getMessage());
        } catch (Exception e) {
            return Result.error("文件预览解析失败：" + e.getMessage());
        }
    }

    Result<Map<String, Object>> preview(String url) {
        return preview(url, null);
    }

    private Path resolveUploadedFile(String rawUrl) {
        if (rawUrl == null || rawUrl.trim().isEmpty()) {
            throw new IllegalArgumentException("文件地址为空");
        }
        String decoded = URLDecoder.decode(rawUrl, StandardCharsets.UTF_8);
        String clean = decoded.split("\\?", 2)[0].replace('\\', '/');
        if (clean.startsWith("http://") || clean.startsWith("https://")) {
            throw new IllegalArgumentException("仅支持本站上传文件预览");
        }
        if (clean.startsWith("/uploads/training/learning/")
                || clean.startsWith("uploads/training/learning/")) {
            throw new IllegalArgumentException("训练学习文件必须通过受控下载地址访问");
        }
        if (clean.startsWith("/uploads/")) {
            clean = clean.substring("/uploads/".length());
        } else if (clean.startsWith("uploads/")) {
            clean = clean.substring("uploads/".length());
        } else {
            throw new IllegalArgumentException("仅支持 uploads 目录内文件预览");
        }
        Path baseDir = Paths.get(uploadDir).toAbsolutePath().normalize();
        Path target = baseDir.resolve(clean).normalize();
        if (!target.startsWith(baseDir)) {
            throw new IllegalArgumentException("文件路径非法");
        }
        return target;
    }

    private PreviewText extractDocxText(Path file) throws Exception {
        try (ZipFile zipFile = new ZipFile(file.toFile())) {
            ZipEntry documentEntry = zipFile.getEntry("word/document.xml");
            if (documentEntry == null) {
                throw new IllegalArgumentException("DOCX 内容缺少正文文档");
            }
            try (InputStream input = zipFile.getInputStream(documentEntry)) {
                byte[] bytes = input.readAllBytes();
                DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
                factory.setNamespaceAware(true);
                factory.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
                factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
                factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
                factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
                factory.setXIncludeAware(false);
                factory.setExpandEntityReferences(false);
                DocumentBuilder builder = factory.newDocumentBuilder();
                builder.setEntityResolver((publicId, systemId) -> new InputSource(new StringReader("")));
                Document document = builder.parse(new ByteArrayInputStream(bytes));

                StringBuilder text = new StringBuilder();
                NodeList paragraphs = document.getElementsByTagNameNS("*", "p");
                for (int i = 0; i < paragraphs.getLength(); i++) {
                    Element paragraph = (Element) paragraphs.item(i);
                    NodeList runs = paragraph.getElementsByTagNameNS("*", "t");
                    StringBuilder line = new StringBuilder();
                    for (int j = 0; j < runs.getLength(); j++) {
                        line.append(runs.item(j).getTextContent());
                    }
                    String normalized = line.toString().trim();
                    if (!normalized.isEmpty()) {
                        appendLine(text, normalized);
                    }
                    if (text.length() >= MAX_TEXT_CHARS) {
                        return new PreviewText(text.substring(0, MAX_TEXT_CHARS), true);
                    }
                }
                String result = text.toString().trim();
                if (result.isEmpty()) {
                    throw new IllegalArgumentException("DOCX 正文为空或暂无法解析");
                }
                return new PreviewText(result, false);
            }
        }
    }

    private PreviewText readPlainText(Path file) throws Exception {
        String text = Files.readString(file, StandardCharsets.UTF_8);
        boolean truncated = text.length() > MAX_TEXT_CHARS;
        return new PreviewText(truncated ? text.substring(0, MAX_TEXT_CHARS) : text, truncated);
    }

    private void appendLine(StringBuilder text, String line) {
        if (text.length() > 0) {
            text.append("\n");
        }
        text.append(line);
    }

    private String extensionOf(String fileName) {
        int dot = fileName.lastIndexOf('.');
        return dot >= 0 ? fileName.substring(dot + 1).toLowerCase(Locale.ROOT) : "";
    }

    private boolean isPlainText(String ext) {
        return "txt".equals(ext) || "md".equals(ext) || "csv".equals(ext) || "json".equals(ext);
    }

    private static class PreviewText {
        private final String text;
        private final boolean truncated;

        private PreviewText(String text, boolean truncated) {
            this.text = text;
            this.truncated = truncated;
        }
    }
}
