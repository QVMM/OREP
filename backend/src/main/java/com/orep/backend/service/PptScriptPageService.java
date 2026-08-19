package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.orep.backend.entity.PptScriptPage;
import com.orep.backend.mapper.PptScriptPageMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.dao.TransientDataAccessException;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class PptScriptPageService {

    @Autowired
    private PptScriptPageMapper mapper;

    public List<PptScriptPage> listByJob(String jobId, Long userId) {
        if (jobId == null || jobId.isBlank() || userId == null) return List.of();
        return mapper.selectList(
                new LambdaQueryWrapper<PptScriptPage>()
                        .eq(PptScriptPage::getJobId, jobId)
                        .eq(PptScriptPage::getCreatedBy, userId)
                        .orderByAsc(PptScriptPage::getPageIndex)
        );
    }

    public PptScriptPage getByPage(String jobId, Integer pageIndex, Long userId) {
        if (jobId == null || jobId.isBlank() || pageIndex == null || userId == null) return null;
        return mapper.selectOne(
                new LambdaQueryWrapper<PptScriptPage>()
                        .eq(PptScriptPage::getJobId, jobId)
                        .eq(PptScriptPage::getPageIndex, pageIndex)
                        .eq(PptScriptPage::getCreatedBy, userId)
        );
    }

    public PptScriptPage savePage(
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
        String safeNotes = notes == null ? "" : notes;
        if (safeNotes.length() > 4000) {
            safeNotes = safeNotes.substring(0, 4000);
        }
        PptScriptPage page = getByPage(jobId, pageIndex, userId);
        LocalDateTime now = LocalDateTime.now();
        if (page == null) {
            page = new PptScriptPage();
            page.setJobId(jobId);
            page.setPageIndex(pageIndex);
            page.setCreatedBy(userId);
            page.setCreatedAt(now);
        }
        applyPageFields(page, pageName, pageTitle, safeNotes, documentJson, source, manualEdited, now);
        if (page.getId() == null) {
            try {
                PptScriptPage newPage = page;
                runDbWrite(() -> mapper.insert(newPage));
            } catch (DuplicateKeyException ex) {
                PptScriptPage existing = getByPage(jobId, pageIndex, userId);
                if (existing == null) {
                    throw ex;
                }
                page.setId(existing.getId());
                page.setCreatedAt(existing.getCreatedAt());
                updateMutableFields(page);
            }
        } else {
            updateMutableFields(page);
        }
        return page;
    }

    public boolean deletePage(String jobId, Integer pageIndex, Long userId) {
        PptScriptPage page = getByPage(jobId, pageIndex, userId);
        if (page == null) return false;
        return mapper.deleteById(page.getId()) > 0;
    }

    private void applyPageFields(
            PptScriptPage page,
            String pageName,
            String pageTitle,
            String notes,
            String documentJson,
            String source,
            Boolean manualEdited,
            LocalDateTime updatedAt
    ) {
        page.setPageName(pageName);
        page.setPageTitle(pageTitle);
        page.setNotes(notes);
        page.setDocumentJson(documentJson);
        page.setSource(source == null || source.isBlank() ? "ppt-editor" : source);
        page.setManualEdited(Boolean.TRUE.equals(manualEdited));
        page.setUpdatedAt(updatedAt);
    }

    private void updateMutableFields(PptScriptPage page) {
        runDbWrite(() -> mapper.update(
                null,
                new LambdaUpdateWrapper<PptScriptPage>()
                        .eq(PptScriptPage::getId, page.getId())
                        .eq(PptScriptPage::getCreatedBy, page.getCreatedBy())
                        .set(PptScriptPage::getPageName, page.getPageName())
                        .set(PptScriptPage::getPageTitle, page.getPageTitle())
                        .set(PptScriptPage::getNotes, page.getNotes())
                        .set(PptScriptPage::getDocumentJson, page.getDocumentJson())
                        .set(PptScriptPage::getSource, page.getSource())
                        .set(PptScriptPage::getManualEdited, page.getManualEdited())
                        .set(PptScriptPage::getUpdatedAt, page.getUpdatedAt())
        ));
    }

    private void runDbWrite(Runnable action) {
        int attempts = 0;
        while (true) {
            try {
                action.run();
                return;
            } catch (RuntimeException ex) {
                attempts++;
                if (attempts >= 4 || !isRetryableLockError(ex)) {
                    throw ex;
                }
                sleepBeforeRetry(attempts);
            }
        }
    }

    private boolean isRetryableLockError(Throwable ex) {
        if (ex instanceof TransientDataAccessException) {
            return true;
        }
        String message = String.valueOf(ex.getMessage()).toLowerCase();
        Throwable cause = ex.getCause();
        while (cause != null) {
            message += " " + String.valueOf(cause.getMessage()).toLowerCase();
            cause = cause.getCause();
        }
        return message.contains("deadlock")
                || message.contains("lock wait timeout")
                || message.contains("try restarting transaction");
    }

    private void sleepBeforeRetry(int attempts) {
        try {
            Thread.sleep(80L * attempts);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Interrupted while retrying script page save", interrupted);
        }
    }
}
