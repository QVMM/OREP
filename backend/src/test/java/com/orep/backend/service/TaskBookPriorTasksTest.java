package com.orep.backend.service;

import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TaskBookPriorTasksTest {

    @Test
    void verifiedWithoutEvidenceIsNotAccepted() {
        TaskBook book = book("补齐差异与仓库证据", null);
        List<ScoreGapCalculator.PriorTask> tasks = TaskBookPriorTasks.from(book, List.of(
                Map.of("reason", "补齐差异与仓库证据", "minimumAcceptancePassed", true, "status", "verified")
        ));
        assertEquals(1, tasks.size());
        assertFalse(tasks.get(0).accepted);
        assertFalse(tasks.get(0).evidenceAttached);
    }

    @Test
    void hangAloneIsNotAccepted() {
        TaskBook book = book("补齐差异与仓库证据", "https://git.example/diff");
        List<ScoreGapCalculator.PriorTask> tasks = TaskBookPriorTasks.from(book, List.of());
        assertTrue(tasks.get(0).evidenceAttached);
        assertFalse(tasks.get(0).accepted);
    }

    @Test
    void verifiedAndHungIsAccepted() {
        TaskBook book = book("补齐差异与仓库证据", "https://git.example/diff");
        List<ScoreGapCalculator.PriorTask> tasks = TaskBookPriorTasks.from(book, List.of(
                Map.of(
                        "reason", "补齐差异与仓库证据 已对照仓库提交",
                        "minimumAcceptancePassed", true,
                        "status", "verified"
                )
        ));
        assertTrue(tasks.get(0).evidenceAttached);
        assertTrue(tasks.get(0).accepted);
    }

    private static TaskBook book(String title, String hung) {
        TaskBook itemBook = new TaskBook();
        itemBook.setPublished(true);
        TaskBookItem item = new TaskBookItem();
        item.setTitle(title);
        item.setHungEvidence(hung);
        item.setExpectedGain("+2~4，下场对照，不保证");
        itemBook.setItems(List.of(item));
        return itemBook;
    }
}
