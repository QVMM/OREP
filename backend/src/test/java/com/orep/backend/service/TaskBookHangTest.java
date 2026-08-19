package com.orep.backend.service;

import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TaskBookHangTest {

    @Test
    void hangWritesEvidenceWithoutChangingTitle() {
        TaskBook hung = TaskBookHang.hang(publishedBook(), 0, " 仓库 https://git.example/diff ", 10L, "2026-08-18T12:00");
        assertEquals("补齐差异与仓库证据", hung.getItems().get(0).getTitle());
        assertEquals("仓库 https://git.example/diff", hung.getItems().get(0).getHungEvidence());
        assertEquals(10L, hung.getItems().get(0).getHungByUserId());
        assertTrue(TaskBookHang.hasHungEvidence(hung.getItems().get(0)));
        assertFalse(TaskBookHang.hasHungEvidence(hung.getItems().get(1)));
    }

    @Test
    void progressCountsHungWithoutCallingItClosure() {
        TaskBook book = publishedBook();
        book.getItems().get(0).setHungEvidence("仓库页");
        TaskBookHang.Progress progress = TaskBookHang.progress(book);
        assertEquals(1, progress.hung());
        assertEquals(2, progress.total());
        assertEquals("已回挂 1/2", progress.display());
    }

    @Test
    void republishKeepsPreviousHangByTitle() {
        TaskBook previous = publishedBook();
        previous.getItems().get(0).setHungEvidence("仓库对比页");
        previous.getItems().get(0).setHungByUserId(10L);
        TaskBook incoming = publishedBook();
        TaskBook merged = TaskBookHang.mergeHangs(incoming, previous);
        assertEquals("仓库对比页", merged.getItems().get(0).getHungEvidence());
        assertEquals(10L, merged.getItems().get(0).getHungByUserId());
        assertFalse(TaskBookHang.hasHungEvidence(merged.getItems().get(1)));
    }

    @Test
    void incomingHangIsNotOverwritten() {
        TaskBook previous = publishedBook();
        previous.getItems().get(0).setHungEvidence("旧回挂");
        TaskBook incoming = publishedBook();
        incoming.getItems().get(0).setHungEvidence("新回挂");
        TaskBook merged = TaskBookHang.mergeHangs(incoming, previous);
        assertEquals("新回挂", merged.getItems().get(0).getHungEvidence());
    }

    @Test
    void blankOrUnpublishedRejected() {
        assertThrows(IllegalArgumentException.class, () -> TaskBookHang.hang(publishedBook(), 0, "  ", 10L, "t"));
        TaskBook draft = publishedBook();
        draft.setPublished(false);
        assertThrows(IllegalArgumentException.class, () -> TaskBookHang.hang(draft, 0, "证据", 10L, "t"));
        assertThrows(IllegalArgumentException.class, () -> TaskBookHang.hang(publishedBook(), 9, "证据", 10L, "t"));
    }

    private static TaskBook publishedBook() {
        TaskBook book = new TaskBook();
        book.setPublished(true);
        TaskBookItem first = new TaskBookItem();
        first.setTitle("补齐差异与仓库证据");
        TaskBookItem second = new TaskBookItem();
        second.setTitle("补齐对比测试证据");
        book.setItems(List.of(first, second));
        return book;
    }
}
