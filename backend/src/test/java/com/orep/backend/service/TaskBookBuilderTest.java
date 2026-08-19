package com.orep.backend.service;

import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class TaskBookBuilderTest {

    @Test
    void generatedTitlesNeverContainBannedWords() {
        List<TaskBookBuilder.Draft> drafts = new ArrayList<>();
        String[] banned = {
                "加强表达", "优化PPT", "提升创新性", "加强节奏", "优化讲解",
                "提升熟练度", "加强演示", "优化结构", "提升价值", "加强对比"
        };
        for (String title : banned) {
            drafts.add(completeDraft(title, "score-deduction:" + title));
        }
        TaskBook book = TaskBookBuilder.draft(drafts);
        assertEquals(10, drafts.size());
        assertTrue(book.getItems().size() <= 4);
        for (TaskBookItem item : book.getItems()) {
            assertFalse(item.getTitle().contains("加强"));
            assertFalse(item.getTitle().contains("优化"));
            assertFalse(item.getTitle().contains("提升"));
            assertTrue(item.getTitle().length() <= 24);
            assertTrue(item.getExpectedGain().contains("下场对照，不保证"));
            assertFalse(item.getSourceRefs().isEmpty());
        }
    }

    @Test
    void unpublishedBookIsHiddenFromStudentTodos() {
        TaskBook book = TaskBookBuilder.draft(List.of(completeDraft("补齐仓库提交记录", "score-deduction:repo")));
        assertFalse(book.isPublished());
        assertEquals(1, book.getItems().size());
        assertTrue(TaskBookBuilder.studentVisibleItems(book).isEmpty());
    }

    @Test
    void publishedBookExposesAtMostFourItems() {
        List<TaskBookBuilder.Draft> drafts = new ArrayList<>();
        for (int i = 0; i < 6; i++) {
            drafts.add(completeDraft("补齐对比表第" + (i + 1) + "项", "score-deduction:" + i));
        }
        TaskBook book = TaskBookBuilder.published(drafts);
        assertTrue(book.isPublished());
        assertEquals(4, book.getItems().size());
        assertEquals(4, TaskBookBuilder.studentVisibleItems(book).size());
    }

    @Test
    void studentAudienceHidesItemsUntilFrozen() {
        TaskBook published = TaskBookBuilder.published(List.of(completeDraft("补齐仓库提交记录", "score-deduction:repo")));
        assertTrue(TaskBookBuilder.forAudience(published, false, false).getItems().isEmpty());
        assertFalse(TaskBookBuilder.forAudience(published, false, false).isPublished());
        assertEquals(1, TaskBookBuilder.forAudience(published, false, true).getItems().size());
    }

    @Test
    void studentAudienceHidesUnpublishedItems() {
        TaskBook draft = TaskBookBuilder.draft(List.of(completeDraft("补齐仓库提交记录", "score-deduction:repo")));
        assertEquals(1, TaskBookBuilder.forAudience(draft, true).getItems().size());
        assertTrue(TaskBookBuilder.forAudience(draft, false).getItems().isEmpty());
        TaskBook published = TaskBookBuilder.published(List.of(completeDraft("补齐仓库提交记录", "score-deduction:repo")));
        assertEquals(1, TaskBookBuilder.forAudience(published, false).getItems().size());
    }

    @Test
    void dropsItemsWithoutSourceRefs() {
        TaskBookBuilder.Draft draft = completeDraft("补齐测试对比表", null);
        draft.sourceRefs = List.of();
        TaskBook book = TaskBookBuilder.draft(List.of(draft));
        assertTrue(book.getItems().isEmpty());
    }

    private static TaskBookBuilder.Draft completeDraft(String title, String sourceRef) {
        TaskBookBuilder.Draft draft = new TaskBookBuilder.Draft();
        draft.priority = 0;
        draft.title = title;
        draft.reason = title;
        draft.goal = "评委能看见对比表";
        draft.steps = List.of("列出缺口", "补上证据页");
        draft.acceptance = "下场能翻到对比表";
        draft.evidenceNeeded = "对比表或录屏";
        draft.expectedGain = "+2~4";
        draft.ownerRole = "主讲";
        draft.dueHint = "下场前";
        draft.sourceRefs = sourceRef == null ? List.of() : List.of(sourceRef);
        return draft;
    }
}
