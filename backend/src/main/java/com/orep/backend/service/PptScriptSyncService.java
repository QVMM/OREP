package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.entity.PptScriptPage;
import com.orep.backend.entity.Script;
import com.orep.backend.mapper.PptScriptPageMapper;
import com.orep.backend.mapper.ScriptMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.CannotAcquireLockException;
import org.springframework.dao.DeadlockLoserDataAccessException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Supplier;

@Service
public class PptScriptSyncService {

    private static final Logger log = LoggerFactory.getLogger(PptScriptSyncService.class);
    private static final String SOURCE_PPT = "ppt";
    private static final String DEFAULT_ROLE = "主讲人";
    private static final String DEFAULT_PPT_TITLE = "PPT 路演讲稿";
    private static final DateTimeFormatter SCRIPT_TITLE_TIME_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
    private static final int DEADLOCK_RETRY_ATTEMPTS = 4;

    @Autowired
    private PptScriptPageMapper pageMapper;

    @Autowired
    private ScriptMapper scriptMapper;

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final ConcurrentMap<String, ReentrantLock> jobLocks = new ConcurrentHashMap<>();

    public Map<String, Object> listBundle(String jobId, Long userId) {
        return withJobLock(jobId, userId, () -> {
            List<PptScriptPage> pages = listPages(jobId, userId);
            Script script = getScriptByPptJob(jobId, userId);
            Map<String, Object> data = new HashMap<>();
            data.put("jobId", jobId);
            data.put("script", script);
            data.put("pages", pages);
            return data;
        });
    }

    public void ensureScriptsForUser(Long userId) {
        if (userId == null) return;
        List<PptScriptPage> allPages = pageMapper.selectList(
                new LambdaQueryWrapper<PptScriptPage>()
                        .eq(PptScriptPage::getCreatedBy, userId)
                        .orderByAsc(PptScriptPage::getJobId)
                        .orderByAsc(PptScriptPage::getPageIndex)
        );
        Map<String, List<PptScriptPage>> pagesByJob = new LinkedHashMap<>();
        for (PptScriptPage page : allPages) {
            if (page.getJobId() == null || page.getJobId().isBlank()) continue;
            if (page.getNotes() == null || page.getNotes().isBlank()) continue;
            pagesByJob.computeIfAbsent(page.getJobId(), ignored -> new ArrayList<>()).add(page);
        }
        for (Map.Entry<String, List<PptScriptPage>> entry : pagesByJob.entrySet()) {
            String jobId = entry.getKey();
            withJobLock(jobId, userId, () -> {
                List<PptScriptPage> pages = entry.getValue();
                Script script = getScriptByPptJob(jobId, userId);
                if (script == null) {
                    script = ensureScript(jobId, userId, pages);
                    rebuildScriptFromPages(script, pages);
                } else {
                    normalizeScriptTitle(script, pages);
                    boolean changed = linkPagesToScript(pages, script);
                    if (changed || shouldRebuildScript(script, pages)) {
                        rebuildScriptFromPages(script, pages);
                    }
                }
                return null;
            });
        }
    }

    public PptScriptPage getPageForUser(String jobId, Integer pageIndex, Long userId) {
        return getPage(jobId, pageIndex, userId);
    }

    public PptScriptPage savePageAndSync(
            String jobId,
            Integer pageIndex,
            String pageName,
            String pageTitle,
            String notes,
            String documentJson,
            String source,
            Boolean manualEdited,
            Long userId
    ) {
        if (jobId == null || jobId.isBlank() || pageIndex == null || pageIndex <= 0 || userId == null) {
            return null;
        }
        return withJobLock(jobId, userId, () -> {
            List<PptScriptPage> existingPages = listPages(jobId, userId);
            Script script = ensureScript(jobId, userId, pagesWithCandidate(existingPages, pageIndex, pageTitle, notes));
            PptScriptPage page = getPage(jobId, pageIndex, userId);
            LocalDateTime now = LocalDateTime.now();
            boolean inserting = page == null;
            if (page == null) {
                page = new PptScriptPage();
                page.setJobId(jobId);
                page.setPageIndex(pageIndex);
                page.setCreatedBy(userId);
                page.setCreatedAt(now);
                page.setVersion(1);
            } else {
                page.setVersion(nextVersion(page.getVersion()));
            }

            String safeNotes = truncate(notes, 4000);
            page.setScriptId(script.getId());
            page.setScriptStepId(stepId(pageIndex));
            page.setPageName(pageName);
            page.setPageTitle(pageTitle);
            page.setNotes(safeNotes);
            page.setDocumentJson(documentJson);
            page.setSource(source == null || source.isBlank() ? "ppt-editor" : source);
            page.setManualEdited(Boolean.TRUE.equals(manualEdited));
            page.setContentHash(hash(safeNotes));
            page.setSyncState("synced");
            page.setLastSyncedAt(now);
            page.setUpdatedAt(now);

            upsertPage(page, inserting);

            List<PptScriptPage> pages = listPages(jobId, userId);
            normalizeScriptTitle(script, pages);
            rebuildScriptFromPages(script, pages);
            return page;
        });
    }

    public boolean deletePageAndSync(String jobId, Integer pageIndex, Long userId) {
        return withJobLock(jobId, userId, () -> {
            PptScriptPage page = getPage(jobId, pageIndex, userId);
            if (page == null) return false;
            runDbWrite("delete ppt script page", () -> pageMapper.deleteById(page.getId()));
            Script script = getScriptByPptJob(jobId, userId);
            if (script != null) {
                rebuildScriptFromPages(script, listPages(jobId, userId));
            }
            return true;
        });
    }

    public void syncScriptToPages(Long scriptId, Long userId) {
        if (scriptId == null || userId == null) return;
        Script script = scriptMapper.selectOne(
                new LambdaQueryWrapper<Script>()
                        .eq(Script::getId, scriptId)
                        .eq(Script::getCreatedBy, userId)
        );
        if (script == null || script.getPptJobId() == null || script.getPptJobId().isBlank()) return;

        withJobLock(script.getPptJobId(), userId, () -> {
            List<Map<String, Object>> steps = extractSteps(script.getContent());
            LocalDateTime now = LocalDateTime.now();
            for (Map<String, Object> step : steps) {
                Integer pageIndex = intValue(step.get("pageIndex"));
                if (pageIndex == null || pageIndex <= 0) continue;
                PptScriptPage page = getPage(script.getPptJobId(), pageIndex, userId);
                if (page == null) continue;

                String notes = truncate(stringValue(step.get("content")), 4000);
                String title = stringValue(step.get("focus"));
                String cleanTitle = title == null || title.isBlank() ? page.getPageTitle() : stripPagePrefix(title);
                boolean changed = !Objects.equals(notes, page.getNotes())
                        || !Objects.equals(cleanTitle, page.getPageTitle())
                        || !Objects.equals(script.getId(), page.getScriptId())
                        || !Objects.equals(stepId(pageIndex), page.getScriptStepId())
                        || !Boolean.TRUE.equals(page.getManualEdited())
                        || !"script-editor".equals(page.getSource())
                        || !"synced".equals(page.getSyncState());
                if (!changed) continue;
                page.setNotes(notes);
                if (cleanTitle != null && !cleanTitle.isBlank()) page.setPageTitle(cleanTitle);
                page.setScriptId(script.getId());
                page.setScriptStepId(stepId(pageIndex));
                page.setManualEdited(true);
                page.setSource("script-editor");
                page.setContentHash(hash(notes));
                page.setVersion(nextVersion(page.getVersion()));
                page.setSyncState("synced");
                page.setLastSyncedAt(now);
                page.setUpdatedAt(now);
                updatePage(page);
            }

            script.setSyncStatus("synced");
            script.setLastSyncedAt(now);
            script.setUpdatedAt(now);
            updateScript(script);
            return null;
        });
    }

    private Script ensureScript(String jobId, Long userId, List<PptScriptPage> pages) {
        Script script = getScriptByPptJob(jobId, userId);
        if (script != null) {
            normalizeScriptTitle(script, pages);
            return script;
        }
        LocalDateTime now = LocalDateTime.now();
        script = new Script();
        script.setMeetingId(null);
        script.setTitle(buildScriptTitle(jobId, pages, now));
        script.setContent("[]");
        script.setRoles("[]");
        script.setSourceType(SOURCE_PPT);
        script.setPptJobId(jobId);
        script.setSyncStatus("synced");
        script.setContentVersion(1);
        script.setLastSyncedAt(now);
        script.setCreatedBy(userId);
        script.setCreatedAt(now);
        script.setUpdatedAt(now);
        insertScript(script);
        return script;
    }

    private void rebuildScriptFromPages(Script script, List<PptScriptPage> pages) {
        LocalDateTime now = LocalDateTime.now();
        List<Map<String, Object>> steps = new ArrayList<>();
        int totalDuration = 0;
        for (PptScriptPage page : pages) {
            String stepId = stepId(page.getPageIndex());
            if (!Objects.equals(script.getId(), page.getScriptId())
                    || !Objects.equals(stepId, page.getScriptStepId())
                    || !"synced".equals(page.getSyncState())) {
                page.setScriptId(script.getId());
                page.setScriptStepId(stepId);
                page.setSyncState("synced");
                page.setLastSyncedAt(now);
                updatePage(page);
            }

            Map<String, Object> step = new LinkedHashMap<>();
            String content = page.getNotes() == null ? "" : page.getNotes();
            int duration = estimateScriptDurationMinutes(content);
            totalDuration += duration;
            step.put("id", stepId);
            step.put("role", DEFAULT_ROLE);
            step.put("duration", duration);
            step.put("focus", focusTitle(page));
            step.put("content", content);
            step.put("notes", "");
            step.put("transition", "");
            step.put("pptJobId", page.getJobId());
            step.put("pageIndex", page.getPageIndex());
            step.put("pageName", page.getPageName());
            step.put("source", "ppt");
            steps.add(step);
        }

        Map<String, Object> chapter = new LinkedHashMap<>();
        chapter.put("id", "ppt-" + script.getPptJobId());
        chapter.put("title", "PPT 页面讲稿");
        chapter.put("totalDuration", Math.max(1, totalDuration));
        chapter.put("steps", steps);

        try {
            String nextContent = objectMapper.writeValueAsString(List.of(chapter));
            if (Objects.equals(nextContent, script.getContent())
                    && SOURCE_PPT.equals(script.getSourceType())
                    && "synced".equals(script.getSyncStatus())) {
                return;
            }
            script.setContent(nextContent);
        } catch (Exception e) {
            script.setContent("[]");
        }
        script.setSourceType(SOURCE_PPT);
        script.setSyncStatus("synced");
        script.setContentVersion(nextVersion(script.getContentVersion()));
        script.setLastSyncedAt(now);
        script.setUpdatedAt(now);
        updateScript(script);
    }

    private List<PptScriptPage> listPages(String jobId, Long userId) {
        if (jobId == null || jobId.isBlank() || userId == null) return List.of();
        return pageMapper.selectList(
                new LambdaQueryWrapper<PptScriptPage>()
                        .eq(PptScriptPage::getJobId, jobId)
                        .eq(PptScriptPage::getCreatedBy, userId)
                        .orderByAsc(PptScriptPage::getPageIndex)
        );
    }

    private PptScriptPage getPage(String jobId, Integer pageIndex, Long userId) {
        if (jobId == null || jobId.isBlank() || pageIndex == null || userId == null) return null;
        List<PptScriptPage> pages = pageMapper.selectList(
                new LambdaQueryWrapper<PptScriptPage>()
                        .eq(PptScriptPage::getJobId, jobId)
                        .eq(PptScriptPage::getPageIndex, pageIndex)
                        .eq(PptScriptPage::getCreatedBy, userId)
                        .orderByDesc(PptScriptPage::getUpdatedAt)
                        .last("LIMIT 1")
        );
        return pages.isEmpty() ? null : pages.get(0);
    }

    private Script getScriptByPptJob(String jobId, Long userId) {
        if (jobId == null || jobId.isBlank() || userId == null) return null;
        List<Script> scripts = scriptMapper.selectList(
                new LambdaQueryWrapper<Script>()
                        .eq(Script::getPptJobId, jobId)
                        .eq(Script::getCreatedBy, userId)
                        .orderByDesc(Script::getUpdatedAt)
                        .last("LIMIT 1")
        );
        return scripts.isEmpty() ? null : scripts.get(0);
    }

    private boolean linkPagesToScript(List<PptScriptPage> pages, Script script) {
        boolean changed = false;
        for (PptScriptPage page : pages) {
            if (script.getId().equals(page.getScriptId()) && stepId(page.getPageIndex()).equals(page.getScriptStepId())) {
                continue;
            }
            page.setScriptId(script.getId());
            page.setScriptStepId(stepId(page.getPageIndex()));
            updatePage(page);
            changed = true;
        }
        return changed;
    }

    private boolean shouldRebuildScript(Script script, List<PptScriptPage> pages) {
        if (script == null || pages.isEmpty()) return false;
        String content = script.getContent();
        if (content == null || content.isBlank() || "[]".equals(content.trim())) return true;

        List<Map<String, Object>> steps = extractSteps(content);
        if (steps.isEmpty()) return true;
        if (steps.size() < pages.size()) return true;

        Map<Integer, String> stepContentByPage = new HashMap<>();
        for (Map<String, Object> step : steps) {
            Integer pageIndex = intValue(step.get("pageIndex"));
            if (pageIndex != null) {
                stepContentByPage.put(pageIndex, stringValue(step.get("content")));
            }
        }
        for (PptScriptPage page : pages) {
            String pageNotes = page.getNotes();
            if (pageNotes == null || pageNotes.isBlank()) continue;
            String scriptContent = stepContentByPage.get(page.getPageIndex());
            if (scriptContent == null || scriptContent.isBlank()) return true;
        }
        return false;
    }

    private List<Map<String, Object>> extractSteps(String content) {
        if (content == null || content.isBlank()) return List.of();
        try {
            List<Map<String, Object>> chapters = objectMapper.readValue(content, new TypeReference<>() {});
            List<Map<String, Object>> steps = new ArrayList<>();
            for (Map<String, Object> chapter : chapters) {
                Object rawSteps = chapter.get("steps");
                if (rawSteps instanceof List<?> list) {
                    for (Object item : list) {
                        if (item instanceof Map<?, ?> raw) {
                            Map<String, Object> step = new HashMap<>();
                            raw.forEach((key, value) -> step.put(String.valueOf(key), value));
                            steps.add(step);
                        }
                    }
                }
            }
            steps.sort(Comparator.comparing(step -> intValue(step.get("pageIndex")), Comparator.nullsLast(Integer::compareTo)));
            return steps;
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<PptScriptPage> pagesWithCandidate(List<PptScriptPage> pages, Integer pageIndex, String pageTitle, String notes) {
        List<PptScriptPage> result = new ArrayList<>(pages == null ? List.of() : pages);
        PptScriptPage candidate = new PptScriptPage();
        candidate.setPageIndex(pageIndex);
        candidate.setPageTitle(pageTitle);
        candidate.setNotes(notes);
        result.add(candidate);
        result.sort(Comparator.comparing(PptScriptPage::getPageIndex, Comparator.nullsLast(Integer::compareTo)));
        return result;
    }

    private void normalizeScriptTitle(Script script, List<PptScriptPage> pages) {
        if (script == null || script.getId() == null) return;
        String expectedTitle = buildScriptTitle(script.getPptJobId(), pages, script.getCreatedAt());
        if (expectedTitle.equals(script.getTitle())) return;
        if (!shouldReplaceScriptTitle(script.getTitle(), pages)) return;
        script.setTitle(expectedTitle);
        script.setUpdatedAt(LocalDateTime.now());
        updateScript(script);
    }

    private <T> T withJobLock(String jobId, Long userId, Supplier<T> supplier) {
        if (jobId == null || jobId.isBlank() || userId == null) {
            return supplier.get();
        }
        String key = userId + ":" + jobId;
        ReentrantLock lock = jobLocks.computeIfAbsent(key, ignored -> new ReentrantLock());
        lock.lock();
        try {
            return supplier.get();
        } finally {
            lock.unlock();
            if (!lock.hasQueuedThreads()) {
                jobLocks.remove(key, lock);
            }
        }
    }

    private void upsertPage(PptScriptPage page, boolean inserting) {
        if (!inserting) {
            updatePage(page);
            return;
        }
        try {
            runDbWrite("insert ppt script page", () -> pageMapper.insert(page));
        } catch (DuplicateKeyException e) {
            PptScriptPage existing = getPage(page.getJobId(), page.getPageIndex(), page.getCreatedBy());
            if (existing == null || existing.getId() == null) throw e;
            page.setId(existing.getId());
            page.setCreatedAt(existing.getCreatedAt());
            page.setVersion(nextVersion(existing.getVersion()));
            updatePage(page);
        }
    }

    private void updatePage(PptScriptPage page) {
        if (page == null || page.getId() == null) return;
        LambdaUpdateWrapper<PptScriptPage> wrapper = new LambdaUpdateWrapper<PptScriptPage>()
                .eq(PptScriptPage::getId, page.getId())
                .set(PptScriptPage::getPageName, page.getPageName())
                .set(PptScriptPage::getPageTitle, page.getPageTitle())
                .set(PptScriptPage::getNotes, page.getNotes())
                .set(PptScriptPage::getDocumentJson, page.getDocumentJson())
                .set(PptScriptPage::getSource, page.getSource())
                .set(PptScriptPage::getManualEdited, page.getManualEdited())
                .set(PptScriptPage::getScriptId, page.getScriptId())
                .set(PptScriptPage::getScriptStepId, page.getScriptStepId())
                .set(PptScriptPage::getContentHash, page.getContentHash())
                .set(PptScriptPage::getVersion, page.getVersion())
                .set(PptScriptPage::getSyncState, page.getSyncState())
                .set(PptScriptPage::getLastSyncedAt, page.getLastSyncedAt())
                .set(PptScriptPage::getUpdatedAt, page.getUpdatedAt());
        runDbWrite("update ppt script page", () -> pageMapper.update(null, wrapper));
    }

    private void insertScript(Script script) {
        runDbWrite("insert ppt script", () -> scriptMapper.insert(script));
    }

    private void updateScript(Script script) {
        runDbWrite("update ppt script", () -> scriptMapper.updateById(script));
    }

    private void runDbWrite(String action, Supplier<Integer> write) {
        RuntimeException last = null;
        for (int attempt = 1; attempt <= DEADLOCK_RETRY_ATTEMPTS; attempt++) {
            try {
                write.get();
                return;
            } catch (RuntimeException e) {
                if (!isDeadlock(e) || attempt == DEADLOCK_RETRY_ATTEMPTS) {
                    throw e;
                }
                last = e;
                long backoffMs = 80L * attempt;
                log.warn("{} hit database deadlock, retrying attempt {}/{} after {}ms",
                        action, attempt + 1, DEADLOCK_RETRY_ATTEMPTS, backoffMs);
                try {
                    Thread.sleep(backoffMs);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                    throw e;
                }
            }
        }
        if (last != null) throw last;
    }

    private boolean isDeadlock(Throwable throwable) {
        Throwable current = throwable;
        while (current != null) {
            if (current instanceof DeadlockLoserDataAccessException || current instanceof CannotAcquireLockException) {
                return true;
            }
            String className = current.getClass().getName();
            String message = current.getMessage() == null ? "" : current.getMessage();
            if (className.contains("MySQLTransactionRollbackException")
                    || message.contains("Deadlock found when trying to get lock")
                    || message.contains("try restarting transaction")) {
                return true;
            }
            current = current.getCause();
        }
        return false;
    }

    private boolean shouldReplaceScriptTitle(String currentTitle, List<PptScriptPage> pages) {
        if (currentTitle == null || currentTitle.isBlank()) return true;
        String title = currentTitle.trim();
        if (title.contains(" · ")) return false;
        if (title.startsWith(DEFAULT_PPT_TITLE)) return true;
        if ("PPT 页面讲稿".equals(title)) return true;
        if (isGenericPageTitle(title)) return true;
        for (PptScriptPage page : pages == null ? List.<PptScriptPage>of() : pages) {
            String pageTitle = sanitizeTitle(page.getPageTitle());
            if (!pageTitle.isBlank() && title.equals(pageTitle)) return true;
        }
        return false;
    }

    private String buildScriptTitle(String jobId, List<PptScriptPage> pages, LocalDateTime titleTime) {
        String pptTitle = extractPptTitle(pages);
        String timeText = (titleTime == null ? LocalDateTime.now() : titleTime).format(SCRIPT_TITLE_TIME_FORMATTER);
        return pptTitle + " · " + timeText;
    }

    private String extractPptTitle(List<PptScriptPage> pages) {
        List<PptScriptPage> safePages = pages == null ? List.of() : pages;
        String coverTitle = safePages.stream()
                .filter(page -> page.getPageIndex() != null && page.getPageIndex() == 1)
                .map(PptScriptPage::getPageTitle)
                .map(this::sanitizeTitle)
                .filter(title -> !title.isBlank() && !isGenericPageTitle(title))
                .findFirst()
                .orElse("");
        if (!coverTitle.isBlank()) return coverTitle;

        String projectTitleFromNotes = safePages.stream()
                .filter(page -> page.getPageIndex() != null && page.getPageIndex() == 1)
                .map(PptScriptPage::getNotes)
                .map(this::extractProjectTitleFromNotes)
                .filter(title -> !title.isBlank())
                .findFirst()
                .orElse("");
        if (!projectTitleFromNotes.isBlank()) return projectTitleFromNotes;

        return safePages.stream()
                .map(PptScriptPage::getPageTitle)
                .map(this::sanitizeTitle)
                .filter(title -> !title.isBlank() && !isGenericPageTitle(title))
                .findFirst()
                .orElse(DEFAULT_PPT_TITLE);
    }

    private String extractProjectTitleFromNotes(String notes) {
        String text = sanitizeTitle(notes);
        if (text.isBlank()) return "";
        String marker = "项目名称";
        int markerIndex = text.indexOf(marker);
        if (markerIndex >= 0) {
            String tail = text.substring(markerIndex + marker.length()).replaceFirst("^[：:：\\s]+", "");
            String title = tail.split("[。；;，,\\n]")[0].trim();
            if (!title.isBlank()) return truncate(title, 80);
        }
        return "";
    }

    private boolean isGenericPageTitle(String title) {
        String value = sanitizeTitle(title);
        return value.isBlank()
                || value.matches("^第\\s*\\d+\\s*页$")
                || value.matches("^Page\\s*\\d+$")
                || value.matches("^P\\d{1,3}$")
                || "目录".equals(value)
                || "封面".equals(value)
                || "首页".equals(value)
                || "结尾".equals(value)
                || "致谢".equals(value)
                || "PPT 页面讲稿".equals(value);
    }

    private String sanitizeTitle(String value) {
        if (value == null) return "";
        return value.replaceAll("\\s+", " ").trim();
    }

    private String focusTitle(PptScriptPage page) {
        String title = page.getPageTitle() == null || page.getPageTitle().isBlank()
                ? "第 " + page.getPageIndex() + " 页"
                : page.getPageTitle();
        return "P" + String.format("%02d", page.getPageIndex()) + " " + title;
    }

    private String stripPagePrefix(String value) {
        return value == null ? null : value.replaceFirst("^P\\d{1,3}\\s+", "").trim();
    }

    private String stepId(Integer pageIndex) {
        return "ppt-page-" + pageIndex;
    }

    private int estimateScriptDurationMinutes(String notes) {
        String compact = notes == null ? "" : notes.replaceAll("\\s+", "");
        if (compact.isBlank()) return 1;
        return Math.max(1, (int) Math.round(compact.length() / 140.0));
    }

    private int nextVersion(Integer version) {
        return version == null || version < 1 ? 1 : version + 1;
    }

    private Integer intValue(Object value) {
        if (value == null) return null;
        if (value instanceof Number number) return number.intValue();
        try {
            return Integer.parseInt(value.toString());
        } catch (Exception ignored) {
            return null;
        }
    }

    private String stringValue(Object value) {
        return value == null ? "" : value.toString();
    }

    private String truncate(String value, int maxLength) {
        String text = value == null ? "" : value;
        return text.length() > maxLength ? text.substring(0, maxLength) : text;
    }

    private String hash(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder();
            for (byte b : bytes) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (Exception ignored) {
            return null;
        }
    }
}
