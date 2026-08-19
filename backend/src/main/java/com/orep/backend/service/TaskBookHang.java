package com.orep.backend.service;

import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;

import java.util.ArrayList;
import java.util.List;

/**
 * Students may hang a URL or note on a published task-book item.
 * A check without hung evidence must not count as closure 100%.
 */
public final class TaskBookHang {
    static final int MAX_EVIDENCE = 500;

    private TaskBookHang() {
    }

    public record Progress(int hung, int total) {
        public String display() {
            if (total <= 0) {
                return "";
            }
            return "已回挂 " + hung + "/" + total;
        }
    }

    public static Progress progress(TaskBook book) {
        if (book == null || book.getItems() == null || book.getItems().isEmpty()) {
            return new Progress(0, 0);
        }
        int total = 0;
        int hung = 0;
        for (TaskBookItem item : book.getItems()) {
            if (item == null || item.getTitle() == null || item.getTitle().isBlank()) {
                continue;
            }
            total++;
            if (hasHungEvidence(item)) {
                hung++;
            }
        }
        return new Progress(hung, total);
    }

    public static boolean hasHungEvidence(TaskBookItem item) {
        return item != null && item.getHungEvidence() != null && !item.getHungEvidence().isBlank();
    }

    public static TaskBook hang(TaskBook book, int index, String evidence, Long userId, String hungAt) {
        if (book == null || !book.isPublished()) {
            throw new IllegalArgumentException("任务书尚未发布");
        }
        List<TaskBookItem> items = book.getItems() == null ? List.of() : book.getItems();
        if (index < 0 || index >= items.size() || items.get(index) == null) {
            throw new IllegalArgumentException("没有这条任务");
        }
        String ref = evidence == null ? "" : evidence.trim();
        if (ref.isEmpty()) {
            throw new IllegalArgumentException("回挂证据不能为空");
        }
        if (ref.length() > MAX_EVIDENCE) {
            throw new IllegalArgumentException("回挂证据过长");
        }
        TaskBook copy = new TaskBook();
        copy.setPublished(true);
        List<TaskBookItem> next = new ArrayList<>();
        for (int i = 0; i < items.size(); i++) {
            TaskBookItem item = items.get(i);
            if (item == null) {
                continue;
            }
            if (i == index) {
                item.setHungEvidence(ref);
                item.setHungAt(hungAt);
                item.setHungByUserId(userId);
            }
            next.add(item);
        }
        copy.setItems(next);
        return copy;
    }

    /**
     * Keep hung evidence when a teacher republishes. Match by title, then sourceRefs.
     * Incoming hang wins; empty incoming inherits the previous hang.
     */
    public static TaskBook mergeHangs(TaskBook incoming, TaskBook previous) {
        if (incoming == null || incoming.getItems() == null || incoming.getItems().isEmpty()) {
            return incoming;
        }
        if (previous == null || previous.getItems() == null || previous.getItems().isEmpty()) {
            return incoming;
        }
        for (TaskBookItem item : incoming.getItems()) {
            if (item == null || hasHungEvidence(item)) {
                continue;
            }
            TaskBookItem matched = matchItem(item, previous.getItems());
            if (matched == null || !hasHungEvidence(matched)) {
                continue;
            }
            item.setHungEvidence(matched.getHungEvidence());
            item.setHungAt(matched.getHungAt());
            item.setHungByUserId(matched.getHungByUserId());
        }
        return incoming;
    }

    private static TaskBookItem matchItem(TaskBookItem item, List<TaskBookItem> previous) {
        String title = item.getTitle() == null ? "" : item.getTitle().trim();
        if (!title.isEmpty()) {
            for (TaskBookItem candidate : previous) {
                if (candidate != null && title.equals(candidate.getTitle() == null ? "" : candidate.getTitle().trim())) {
                    return candidate;
                }
            }
        }
        List<String> refs = item.getSourceRefs() == null ? List.of() : item.getSourceRefs();
        for (String ref : refs) {
            if (ref == null || ref.isBlank()) {
                continue;
            }
            for (TaskBookItem candidate : previous) {
                if (candidate == null || candidate.getSourceRefs() == null) {
                    continue;
                }
                if (candidate.getSourceRefs().contains(ref)) {
                    return candidate;
                }
            }
        }
        return null;
    }
}
