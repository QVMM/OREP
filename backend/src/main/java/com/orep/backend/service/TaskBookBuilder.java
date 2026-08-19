package com.orep.backend.service;

import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Builds at most 4 hard task-book items. Missing required fields or banned titles are dropped.
 * Items are drafts until a teacher publishes them.
 */
public final class TaskBookBuilder {
    private static final Pattern BANNED_TITLE = Pattern.compile("加强|优化|提升");
    private static final Pattern VERB_START = Pattern.compile("^(补齐|录制|写清|对照|补上|列出|准备|展示)");
    private static final int MAX_ITEMS = 4;
    private static final int MAX_TITLE = 24;

    private TaskBookBuilder() {
    }

    public static TaskBook draft(List<Draft> drafts) {
        return build(drafts, false);
    }

    public static TaskBook published(List<Draft> drafts) {
        return build(drafts, true);
    }

    public static List<TaskBookItem> studentVisibleItems(TaskBook book) {
        if (book == null || !book.isPublished() || book.getItems() == null) {
            return List.of();
        }
        return List.copyOf(book.getItems());
    }

    public static TaskBook forAudience(TaskBook book, boolean teacherPreview) {
        return forAudience(book, teacherPreview, true);
    }

    public static TaskBook forAudience(TaskBook book, boolean teacherPreview, boolean frozen) {
        if (book == null || teacherPreview) {
            return book;
        }
        if (!frozen) {
            TaskBook hidden = new TaskBook();
            hidden.setPublished(false);
            hidden.setItems(new ArrayList<>());
            return hidden;
        }
        TaskBook visible = new TaskBook();
        visible.setPublished(book.isPublished());
        visible.setItems(new ArrayList<>(studentVisibleItems(book)));
        return visible;
    }

    public static boolean isBannedTitle(String title) {
        return title != null && BANNED_TITLE.matcher(title).find();
    }

    private static TaskBook build(List<Draft> drafts, boolean published) {
        List<Draft> safe = drafts == null ? List.of() : new ArrayList<>(drafts);
        safe.sort(Comparator.comparingInt(draft -> draft.priority == null ? 1 : draft.priority));
        List<TaskBookItem> items = new ArrayList<>();
        for (Draft draft : safe) {
            if (items.size() >= MAX_ITEMS) {
                break;
            }
            TaskBookItem item = toItem(draft);
            if (item != null) {
                items.add(item);
            }
        }
        TaskBook book = new TaskBook();
        book.setPublished(published);
        book.setItems(items);
        return book;
    }

    private static TaskBookItem toItem(Draft draft) {
        if (draft == null) {
            return null;
        }
        String title = normalizeTitle(draft.title, draft.reason);
        if (!isComplete(title) || isBannedTitle(title) || !VERB_START.matcher(title).find() || title.length() > MAX_TITLE) {
            return null;
        }
        String goal = firstNonBlank(draft.goal, "评委能在 60 秒内看到「" + firstNonBlank(draft.reason, "扣分点") + "」已补上可核验证据。");
        List<String> steps = draft.steps == null ? List.of() : draft.steps.stream().filter(TaskBookBuilder::isComplete).toList();
        if (steps.size() < 2 || steps.size() > 5) {
            steps = defaultSteps(draft.reason);
        }
        String acceptance = firstNonBlank(draft.acceptance, "下场能跳到证据页或指定秒数，对照本场扣分点复核。");
        String evidenceNeeded = firstNonBlank(draft.evidenceNeeded, "下场补上可跳转的运行/对比证据");
        String expectedGain = normalizeGain(draft.expectedGain);
        String ownerRole = firstNonBlank(draft.ownerRole, "主讲");
        String dueHint = firstNonBlank(draft.dueHint, "下场前");
        List<String> sourceRefs = draft.sourceRefs == null ? List.of() : draft.sourceRefs.stream().filter(TaskBookBuilder::isComplete).toList();
        if (sourceRefs.isEmpty()) {
            return null;
        }
        TaskBookItem item = new TaskBookItem();
        item.setTitle(title);
        item.setGoal(goal);
        item.setSteps(steps);
        item.setAcceptance(acceptance);
        item.setEvidenceNeeded(evidenceNeeded);
        item.setExpectedGain(expectedGain);
        item.setOwnerRole(ownerRole);
        item.setDueHint(dueHint);
        item.setSourceRefs(sourceRefs);
        return item;
    }

    private static String normalizeTitle(String title, String reason) {
        String raw = firstNonBlank(title, reason);
        if (raw == null) {
            return "";
        }
        String compact = raw.replaceAll("\\s+", "").replaceFirst("^(加强|优化|提升)", "补齐");
        if (isBannedTitle(compact)) {
            return "";
        }
        if (!VERB_START.matcher(compact).find()) {
            compact = "补齐" + compact;
        }
        if (compact.length() > MAX_TITLE) {
            compact = compact.substring(0, MAX_TITLE);
        }
        return compact;
    }

    private static String normalizeGain(String gain) {
        String raw = firstNonBlank(gain, "+2~4");
        if (!raw.contains("下场对照")) {
            raw = raw + "，下场对照，不保证";
        }
        return raw;
    }

    private static List<String> defaultSteps(String reason) {
        String focus = firstNonBlank(reason, "本场扣分点");
        return List.of(
                "列出「" + focus + "」本场缺的证据",
                "补录或改页，使评委 60 秒内能看见变化"
        );
    }

    private static boolean isComplete(String value) {
        return value != null && !value.isBlank();
    }

    private static String firstNonBlank(String... values) {
        if (values == null) {
            return null;
        }
        for (String value : values) {
            if (value != null && !value.isBlank()) {
                return value.trim();
            }
        }
        return null;
    }

    public static final class Draft {
        public Integer priority;
        public String title;
        public String reason;
        public String goal;
        public List<String> steps;
        public String acceptance;
        public String evidenceNeeded;
        public String expectedGain;
        public String ownerRole;
        public String dueHint;
        public List<String> sourceRefs;
    }
}
