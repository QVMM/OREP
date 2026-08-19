package com.orep.backend.service.roadshow.projection;

/**
 * Block 0 任务模板，不接生成模型。task_focus 是 T2/T3 的任务相关属性。
 */
public final class TaskExpression {

    private TaskExpression() {
    }

    public record Text(String slide, String speaking, String taskFocus) {
    }

    public static Text render(PageIntentSpec intent, ClaimCandidate selected, String painProposition) {
        String fact = selected.extractedFact();
        if ("bridge".equals(intent.role())) {
            return new Text(
                    "这和我们的问题一样：" + painProposition,
                    "从「" + fact + "」可以看到与「" + painProposition + "」同一结构。",
                    "bridge"
            );
        }
        return new Text(
                fact + "——就在当下。",
                "请看这个事件：" + fact,
                "urgency"
        );
    }
}
