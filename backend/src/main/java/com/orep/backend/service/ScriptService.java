package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.Script;
import com.orep.backend.mapper.ScriptMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class ScriptService {

    private static final Logger log = LoggerFactory.getLogger(ScriptService.class);

    private final ScriptMapper scriptMapper;
    private final ScriptRevisionService scriptRevisionService;
    private final InspireOfficeService inspireOfficeService;

    public ScriptService(
            ScriptMapper scriptMapper,
            ScriptRevisionService scriptRevisionService,
            InspireOfficeService inspireOfficeService
    ) {
        this.scriptMapper = scriptMapper;
        this.scriptRevisionService = scriptRevisionService;
        this.inspireOfficeService = inspireOfficeService;
    }

    /** 根据 PPT 任务和创建人获取讲稿，避免不同用户互相看到 PPT 生成讲稿 */
    public Script getByPptJobId(String pptJobId, Long userId) {
        if (pptJobId == null || pptJobId.isBlank() || userId == null) return null;
        List<Script> scripts = scriptMapper.selectList(
                new LambdaQueryWrapper<Script>()
                        .eq(Script::getPptJobId, pptJobId)
                        .eq(Script::getCreatedBy, userId)
                        .orderByDesc(Script::getUpdatedAt)
                        .last("LIMIT 1")
        );
        return scripts.isEmpty() ? null : scripts.get(0);
    }

    /** 根据ID获取讲稿 */
    public Script getById(Long id) {
        return scriptMapper.selectById(id);
    }

    /** 根据ID和创建人获取讲稿 */
    public Script getById(Long id, Long userId) {
        if (id == null || userId == null) return null;
        return scriptMapper.selectOne(
                new LambdaQueryWrapper<Script>()
                        .eq(Script::getId, id)
                        .eq(Script::getCreatedBy, userId)
        );
    }

    /** 创建或更新讲稿（自动保存） */
    public Script saveScript(String title, String content, String roles, Long userId) {
        return saveScript(title, content, roles, userId, "manual", null);
    }

    /** 创建或更新讲稿，PPT 讲稿只通过 pptJobId + userId 归属。 */
    public Script saveScript(String title, String content, String roles, Long userId, String sourceType, String pptJobId) {
        String normalizedPptJobId = pptJobId == null || pptJobId.isBlank() ? null : pptJobId;
        String normalizedSourceType = normalizedPptJobId == null ? normalizeSourceType(sourceType) : "ppt";
        Script existing = normalizedPptJobId == null ? null : getByPptJobId(normalizedPptJobId, userId);
        if (existing != null) {
            existing.setTitle(title);
            existing.setContent(content);
            existing.setRoles(roles);
            existing.setMeetingId(null);
            existing.setSourceType(normalizedSourceType);
            existing.setPptJobId(normalizedPptJobId);
            existing.setSyncStatus("synced");
            existing.setContentVersion(nextVersion(existing.getContentVersion()));
            existing.setLastSyncedAt(LocalDateTime.now());
            existing.setUpdatedAt(LocalDateTime.now());
            scriptMapper.updateById(existing);
            return existing;
        } else {
            Script script = new Script();
            script.setMeetingId(null);
            script.setTitle(title);
            script.setContent(content);
            script.setRoles(roles);
            script.setSourceType(normalizedSourceType);
            script.setPptJobId(normalizedPptJobId);
            script.setSyncStatus("synced");
            script.setContentVersion(1);
            script.setLastSyncedAt(LocalDateTime.now());
            script.setCreatedBy(userId);
            script.setCreatedAt(LocalDateTime.now());
            script.setUpdatedAt(LocalDateTime.now());
            scriptMapper.insert(script);
            return script;
        }
    }

    /**
     * 小启确认后的步骤补丁：鉴权、版本闸、快照、只改允许字段。
     */
    @Transactional
    public Script applyPatches(Long scriptId, Long userId, Integer expectedVersion, List<Map<String, Object>> patches) {
        Script script = getById(scriptId, userId);
        if (script == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "讲稿不存在或无权访问");
        }
        int current = currentVersion(script.getContentVersion());
        if (expectedVersion == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少 expectedVersion");
        }
        if (expectedVersion != current) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "讲稿已更新，请刷新后再确认");
        }
        scriptRevisionService.snapshot(script, userId, "apply_script_patch");
        String next;
        try {
            next = ScriptPatchApplier.apply(script.getContent(), patches);
        } catch (IllegalStateException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, e.getMessage());
        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, e.getMessage());
        }
        script.setContent(next);
        script.setSyncStatus(script.getPptJobId() != null && !script.getPptJobId().isBlank() ? "script_newer" : "synced");
        script.setContentVersion(nextVersion(script.getContentVersion()));
        script.setUpdatedAt(LocalDateTime.now());
        scriptMapper.updateById(script);
        patchBoundSdoc(script, userId, patches);
        return script;
    }

    /**
     * 启发 Office 智能文档即讲稿：打开文档时自动创建或挂上 script。
     */
    @Transactional
    public Map<String, Object> ensureForSdoc(Long documentId, Long userId) {
        if (documentId == null || userId == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "缺少文档");
        }
        var doc = inspireOfficeService.requireAccessible(documentId, userId);
        String ext = doc.getExt() == null ? "" : doc.getExt().replace(".", "").toLowerCase();
        if (!"sdoc".equals(ext)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "只有智能文档可以当作讲稿");
        }
        Script script = getBySdocDocumentId(documentId, userId);
        String json = inspireOfficeService.readSmartDocContent(documentId);
        if (script == null) {
            script = new Script();
            script.setTitle(doc.getTitle() == null || doc.getTitle().isBlank() ? "未命名讲稿" : doc.getTitle());
            script.setContent(ScriptSdocCodec.defaultChaptersJson(ScriptSdocCodec.extractPlainText(json)));
            script.setRoles("[{\"id\":\"r1\",\"label\":\"主讲人\",\"color\":\"#409EFF\"}]");
            script.setSourceType("manual");
            script.setSyncStatus("synced");
            script.setContentVersion(1);
            script.setSdocDocumentId(documentId);
            script.setCreatedBy(userId);
            script.setCreatedAt(LocalDateTime.now());
            script.setUpdatedAt(LocalDateTime.now());
            scriptMapper.insert(script);
        }
        String next = ScriptSdocCodec.ensureSheet(json, script);
        boolean changed = next != null && !next.equals(json);
        if (changed) {
            inspireOfficeService.replaceSmartDocContent(documentId, userId, next);
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", script.getId());
        out.put("scriptId", script.getId());
        out.put("title", script.getTitle());
        out.put("contentVersion", currentVersion(script.getContentVersion()));
        out.put("pptJobId", script.getPptJobId());
        out.put("sdocDocumentId", documentId);
        out.put("content", next);
        out.put("contentChanged", changed);
        return out;
    }

    public Script getBySdocDocumentId(Long documentId, Long userId) {
        if (documentId == null || userId == null) return null;
        return scriptMapper.selectOne(
                new LambdaQueryWrapper<Script>()
                        .eq(Script::getSdocDocumentId, documentId)
                        .eq(Script::getCreatedBy, userId)
                        .last("LIMIT 1")
        );
    }

    @Transactional
    public Map<String, Object> openWorkbenchSdoc(Long scriptId, Long userId, Long tenantId, String role) {
        Script script = getById(scriptId, userId);
        if (script == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "讲稿不存在或无权访问");
        }
        Long docId = script.getSdocDocumentId();
        boolean reuse = false;
        if (docId != null) {
            try {
                inspireOfficeService.requireAccessible(docId, userId);
                reuse = true;
            } catch (Exception ignored) {
                docId = null;
            }
        }
        if (reuse) {
            try {
                String existing = inspireOfficeService.readSmartDocContent(docId);
                String merged = ScriptSdocCodec.mergeIntoScript(script.getContent(), existing);
                if (merged != null && !merged.equals(script.getContent())) {
                    script.setContent(merged);
                    script.setUpdatedAt(LocalDateTime.now());
                    scriptMapper.updateById(script);
                }
            } catch (Exception e) {
                log.warn("merge sdoc into script failed script={}: {}", scriptId, e.getMessage());
            }
        } else {
            try {
                Map<String, Object> view = inspireOfficeService.createBlank(
                        userId, tenantId, role, script.getTitle(), "sdoc", "personal", null);
                Object idVal = view.get("id");
                if (!(idVal instanceof Number n)) {
                    throw new IllegalStateException("新建智能文档失败");
                }
                docId = n.longValue();
                script.setSdocDocumentId(docId);
                script.setUpdatedAt(LocalDateTime.now());
                scriptMapper.updateById(script);
            } catch (ResponseStatusException e) {
                throw e;
            } catch (Exception e) {
                throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "创建改稿文档失败：" + e.getMessage());
            }
        }
        try {
            inspireOfficeService.replaceSmartDocContent(docId, userId, ScriptSdocCodec.fromScript(script));
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "写入改稿文档失败：" + e.getMessage());
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("documentId", docId);
        out.put("scriptId", script.getId());
        out.put("contentVersion", currentVersion(script.getContentVersion()));
        out.put("pptJobId", script.getPptJobId());
        out.put("title", script.getTitle());
        return out;
    }

    /**
     * 对照/编译用：智能文档里的正文优先。不覆盖用户文档，只填内存里的讲稿步骤。
     */
    public Script hydrateFromSmartDoc(Script script, Long userId) {
        if (script == null) return null;
        try {
            if (script.getId() != null) {
                script = syncFromSdoc(script.getId(), userId);
            }
        } catch (Exception e) {
            log.warn("sync sdoc before compile failed script={}: {}", script.getId(), e.getMessage());
        }
        if (hasSpoken(script.getContent())) return script;
        Long docId = script.getSdocDocumentId();
        if (docId == null) {
            docId = inspireOfficeService.latestSmartDocId(userId);
        }
        if (docId == null) return script;
        try {
            String json = inspireOfficeService.readSmartDocContent(docId);
            String chapters = ScriptSdocCodec.chaptersFromDocument(json);
            if (chapters != null) {
                script.setContent(chapters);
            }
        } catch (Exception e) {
            log.warn("read sdoc for compile failed script={} doc={}: {}", script.getId(), docId, e.getMessage());
        }
        return script;
    }

    /** 讲稿页数按结构估，不靠翻页标记。健康区间 38–45。 */
    public Map<String, Object> pageMeter(Long scriptId, Long userId) {
        Script script = getById(scriptId, userId);
        int n = 0;
        if (script != null) {
            Long docId = script.getSdocDocumentId();
            if (docId == null) {
                docId = inspireOfficeService.latestSmartDocId(userId);
            }
            if (docId != null) {
                try {
                    n = ScriptSdocCodec.pageCountFromDocument(inspireOfficeService.readSmartDocContent(docId));
                } catch (Exception e) {
                    log.warn("count script pages failed script={} doc={}: {}", scriptId, docId, e.getMessage());
                }
            }
            if (n == 0 && script.getContent() != null) {
                StringBuilder joined = new StringBuilder();
                for (Map<String, Object> step : ScriptScoreRevisePlanner.flattenSteps(script.getContent())) {
                    joined.append(step.getOrDefault("content", "")).append('\n');
                }
                n = ScriptSdocCodec.pageCountFromPlain(joined.toString());
            }
        }
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("scriptId", scriptId);
        out.put("scriptPageCount", n);
        out.put("pageHealth", ScriptSdocCodec.pageHealth(n));
        out.put("pageHealthLabel", ScriptSdocCodec.pageHealthLabel(n));
        return out;
    }

    static boolean hasSpoken(String chaptersJson) {
        return ScriptScoreRevisePlanner.flattenSteps(chaptersJson).stream()
                .anyMatch(s -> {
                    String c = String.valueOf(s.getOrDefault("content", "")).trim();
                    return c.length() >= 4;
                });
    }

    @Transactional
    public Script syncFromSdoc(Long scriptId, Long userId) {
        Script script = getById(scriptId, userId);
        if (script == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "讲稿不存在或无权访问");
        }
        if (script.getSdocDocumentId() == null) {
            return script;
        }
        try {
            String json = inspireOfficeService.readSmartDocContent(script.getSdocDocumentId());
            String merged = ScriptSdocCodec.mergeIntoScript(script.getContent(), json);
            if (merged == null || merged.equals(script.getContent())) {
                return script;
            }
            script.setContent(merged);
            script.setSyncStatus(script.getPptJobId() != null && !script.getPptJobId().isBlank() ? "script_newer" : "synced");
            script.setContentVersion(nextVersion(script.getContentVersion()));
            script.setUpdatedAt(LocalDateTime.now());
            scriptMapper.updateById(script);
            return script;
        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "同步讲稿失败：" + e.getMessage());
        }
    }

    private void patchBoundSdoc(Script script, Long userId, List<Map<String, Object>> patches) {
        if (script == null || script.getSdocDocumentId() == null || patches == null) return;
        try {
            String json = inspireOfficeService.readSmartDocContent(script.getSdocDocumentId());
            String next = ScriptSdocCodec.applyContentPatches(json, patches);
            inspireOfficeService.replaceSmartDocContent(script.getSdocDocumentId(), userId, next);
        } catch (Exception e) {
            log.warn("patch bound sdoc failed script={}: {}", script.getId(), e.getMessage());
        }
    }

    /** 部分更新内容（自动保存用） */
    public Script updateContent(Long id, String title, String content, String roles, Long userId) {
        Script script = getById(id, userId);
        if (script == null) return null;
        if (title != null && !title.isBlank()) script.setTitle(title.trim());
        script.setContent(content);
        if (roles != null) script.setRoles(roles);
        script.setSyncStatus(script.getPptJobId() != null && !script.getPptJobId().isBlank() ? "script_newer" : "synced");
        script.setContentVersion(nextVersion(script.getContentVersion()));
        script.setUpdatedAt(LocalDateTime.now());
        scriptMapper.updateById(script);
        return script;
    }

    /** 删除讲稿 */
    public boolean deleteScript(Long id, Long userId) {
        Script script = getById(id, userId);
        if (script == null) return false;
        return scriptMapper.deleteById(id) > 0;
    }

    /** 获取用户创建的所有讲稿 */
    public List<Script> listByUserId(Long userId) {
        return scriptMapper.selectList(
                new LambdaQueryWrapper<Script>().eq(Script::getCreatedBy, userId)
                        .orderByDesc(Script::getUpdatedAt)
        );
    }

    public void updateSyncState(Script script, String syncStatus) {
        if (script == null || script.getId() == null) return;
        script.setSyncStatus(syncStatus == null || syncStatus.isBlank() ? "synced" : syncStatus);
        script.setContentVersion(nextVersion(script.getContentVersion()));
        script.setLastSyncedAt(LocalDateTime.now());
        script.setUpdatedAt(LocalDateTime.now());
        scriptMapper.updateById(script);
    }

    private String normalizeSourceType(String sourceType) {
        if ("ppt".equalsIgnoreCase(sourceType)) return "ppt";
        return "manual";
    }

    private int nextVersion(Integer version) {
        return version == null || version < 1 ? 1 : version + 1;
    }

    static int currentVersion(Integer version) {
        return version == null || version < 1 ? 1 : version;
    }
}
