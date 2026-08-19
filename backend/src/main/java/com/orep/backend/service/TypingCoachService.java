package com.orep.backend.service;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * 打字 AI 教练（规则引擎）。
 * 返回结构与前端 coach.js 对齐，便于后续替换为 LLM 润色。
 */
@Service
public class TypingCoachService {

    public Map<String, Object> coach(Map<String, Object> body) {
        Map<String, Object> result = asMap(body.get("result"));
        if (result == null) result = body;

        int cpm = intVal(result.get("cpm"), 0);
        double accuracy = doubleVal(result.get("accuracy"), 0);
        int correctChars = intVal(result.get("correctChars"), 0);
        long elapsedMs = longVal(result.get("elapsedMs"), 0L);
        String mode = text(result.get("mode"), "practice").toLowerCase(Locale.ROOT);
        boolean ranked = "ranked".equals(mode);

        List<Map<String, Object>> weakChars = extractWeak(result);
        List<Map<String, Object>> issues = new ArrayList<>();
        List<String> tips = new ArrayList<>();
        String level = "steady";

        if (accuracy < 88) {
            level = "focus";
            issues.add(issue("accuracy_low", "准确率偏低",
                    "本局准确率 " + accuracy + "%，建议先降速、减少回改，把正确率拉回 92% 以上。"));
        } else if (accuracy < 94) {
            issues.add(issue("accuracy_mid", "准确率仍有提升空间",
                    "准确率 " + accuracy + "%，接近稳定区。可把注意力放在标点与数字上。"));
        }

        if (cpm > 0 && cpm < 40 && accuracy >= 90) {
            issues.add(issue("speed_low", "速度偏保守",
                    "净速度 " + cpm + " CPM，正确率尚可。下一局可用短冲刺（1～2 分钟）找节奏。"));
        }
        if (cpm >= 80 && accuracy < 92) {
            level = "focus";
            issues.add(issue("speed_over_acc", "速度压过了准确",
                    "冲得快但错字偏多。建议先「准」再「快」，否则排位净速度会被拖累。"));
        }
        if (weakChars.size() >= 3) {
            String sample = weakChars.stream().limit(5)
                    .map(w -> String.valueOf(w.get("char")))
                    .reduce((a, b) -> a + "、" + b).orElse("");
            issues.add(issue("weak_chars", "存在集中易错字",
                    "高频错字：" + sample + "。建议用「薄弱攻坚」专项练这些字。"));
        }
        if (ranked && elapsedMs < 5 * 60 * 1000L && correctChars < 200) {
            issues.add(issue("ranked_short", "排位有效输出不足",
                    "排位赛要拼持续输出。下一局尽量稳住前 5 分钟节奏，再加速。"));
        }

        if (issues.isEmpty()) {
            issues.add(issue("stable", "本局发挥稳定",
                    "没有突出短板。可以适当加时长，或挑战排位赛检验耐力。"));
            if (accuracy >= 96 && cpm >= 60) level = "great";
        } else if ("focus".equals(level) == false && accuracy >= 96 && cpm >= 70) {
            level = "great";
        }

        String headline;
        if ("great".equals(level)) {
            headline = ranked
                    ? "排位发挥出色：" + cpm + " CPM · " + accuracy + "% 准确率"
                    : "状态在线：" + cpm + " CPM，准确率 " + accuracy + "%";
        } else if ("focus".equals(level)) {
            headline = accuracy < 90
                    ? "先把准确率拉起来，速度会跟着上来"
                    : "本局有明显可改进点，按处方练更有效";
        } else {
            headline = ranked
                    ? "排位已记录：" + cpm + " CPM · 继续稳准节奏"
                    : "本局完成：" + cpm + " CPM · " + accuracy + "% 准确率";
        }

        if (accuracy >= 95 && cpm >= 50) {
            tips.add("正确率已经很好，下一局可尝试略提速，但仍以不掉准为准。");
        }
        if (ranked) {
            tips.add("排位文案固定，多打几次会形成肌肉记忆，重点练开场与数据句。");
        }
        if (tips.isEmpty()) {
            tips.add("每天固定练几分钟，比偶尔突击更有效。");
        }

        Map<String, Object> prescription = buildPrescription(level, accuracy, cpm, weakChars, ranked, issues);

        Map<String, Object> out = new HashMap<>();
        out.put("source", "rule_coach_v1");
        out.put("level", level);
        out.put("headline", headline);
        out.put("summary", String.valueOf(issues.get(0).get("detail")));
        out.put("issues", issues.size() > 3 ? issues.subList(0, 3) : issues);
        out.put("tips", tips.size() > 3 ? tips.subList(0, 3) : tips);
        out.put("weakChars", weakChars.size() > 12 ? weakChars.subList(0, 12) : weakChars);
        out.put("prescription", prescription);
        return out;
    }

    private Map<String, Object> buildPrescription(
            String level, double accuracy, int cpm,
            List<Map<String, Object>> weakChars, boolean ranked,
            List<Map<String, Object>> issues
    ) {
        boolean needDrill = weakChars.size() >= 2 || issues.stream().anyMatch(i -> {
            String id = String.valueOf(i.get("id"));
            return "weak_chars".equals(id) || "accuracy_low".equals(id);
        });
        List<String> weak = weakChars.stream()
                .map(w -> String.valueOf(w.get("char")))
                .filter(s -> s != null && !s.isBlank() && !"null".equals(s))
                .limit(10)
                .toList();

        Map<String, Object> p = new HashMap<>();
        if (needDrill && !weak.isEmpty()) {
            p.put("id", "drill_weak");
            p.put("mode", "practice");
            p.put("label", "薄弱攻坚");
            p.put("title", "按薄弱字专项练 3 分钟");
            p.put("reason", "集中消灭本局/近期易错字，比重复舒适区更有效。");
            p.put("durationSec", 180);
            p.put("lang", "zh");
            p.put("difficulty", 2);
            p.put("drill", true);
            p.put("weakChars", weak);
            p.put("customText", buildDrillText(weak, 280));
            p.put("cta", "开始薄弱攻坚");
            return p;
        }
        if (accuracy < 92) {
            p.put("id", "slow_acc");
            p.put("mode", "practice");
            p.put("label", "稳准练习");
            p.put("title", "5 分钟稳准局（降难度）");
            p.put("reason", "准确率未达标时，优先降速练准，避免错误动力定型。");
            p.put("durationSec", 300);
            p.put("lang", "zh");
            p.put("difficulty", 1);
            p.put("drill", false);
            p.put("weakChars", weak);
            p.put("customText", "");
            p.put("cta", "开始稳准练习");
            return p;
        }
        if (cpm < 45 && accuracy >= 92) {
            p.put("id", "speed_burst");
            p.put("mode", "practice");
            p.put("label", "速度冲刺");
            p.put("title", "2 分钟速度冲刺");
            p.put("reason", "正确率尚可，用短冲刺唤醒指速，再回到常规时长。");
            p.put("durationSec", 120);
            p.put("lang", "zh");
            p.put("difficulty", 2);
            p.put("drill", false);
            p.put("weakChars", weak);
            p.put("customText", "");
            p.put("cta", "开始速度冲刺");
            return p;
        }
        if (!ranked && ("great".equals(level) || (cpm >= 55 && accuracy >= 94))) {
            p.put("id", "go_ranked");
            p.put("mode", "ranked");
            p.put("label", "排位检验");
            p.put("title", "去打一局排位赛");
            p.put("reason", "自主练习状态不错，用 10 分钟固定赛题检验持续输出。");
            p.put("durationSec", 600);
            p.put("lang", "zh");
            p.put("difficulty", 2);
            p.put("drill", false);
            p.put("weakChars", weak);
            p.put("customText", "");
            p.put("cta", "进入排位赛");
            return p;
        }
        p.put("id", "balanced");
        p.put("mode", "practice");
        p.put("label", "均衡巩固");
        p.put("title", "再来 5 分钟均衡练习");
        p.put("reason", "保持当前节奏，巩固手感即可。");
        p.put("durationSec", 300);
        p.put("lang", "zh");
        p.put("difficulty", 2);
        p.put("drill", false);
        p.put("weakChars", weak);
        p.put("customText", "");
        p.put("cta", "按建议再练");
        return p;
    }

    private String buildDrillText(List<String> weak, int targetLen) {
        String[] templates = {
                "路演时要把重点说清楚：问题、方案、证据、下一步。",
                "开场先讲清为谁解决什么问题，再展开路径与结果。",
                "数据要有对比：提升多少、基线是什么、如何验证。",
                "团队分工明确，演示节奏稳定，问答先结论后依据。",
                "练习准确优先，再逐步提速，保持呼吸与坐姿稳定。"
        };
        StringBuilder sb = new StringBuilder();
        int i = 0;
        while (sb.length() < targetLen && i < 40) {
            sb.append(templates[i % templates.length]);
            for (String ch : weak) {
                if (ch != null && !ch.isBlank()) sb.append(ch);
            }
            String rev = String.join("", weak);
            sb.append(new StringBuilder(rev).reverse());
            i++;
        }
        String text = sb.toString().replaceAll("\\s+", "");
        if (text.length() > targetLen) text = text.substring(0, targetLen);
        return text;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> extractWeak(Map<String, Object> result) {
        List<Map<String, Object>> list = new ArrayList<>();
        Object top = result.get("topErrors");
        if (top instanceof List<?> arr) {
            for (Object o : arr) {
                if (o instanceof Map<?, ?> m) {
                    Object ch = m.get("char");
                    if (ch == null) continue;
                    String s = String.valueOf(ch);
                    if (s.isBlank() || " ".equals(s) || "\n".equals(s)) continue;
                    Map<String, Object> row = new HashMap<>();
                    row.put("char", s);
                    row.put("count", intVal(m.get("count"), 1));
                    list.add(row);
                }
            }
        }
        if (!list.isEmpty()) return list;
        Object mapObj = result.get("errorMap");
        if (mapObj instanceof Map<?, ?> em) {
            for (Map.Entry<?, ?> e : em.entrySet()) {
                String s = String.valueOf(e.getKey());
                if (s.isBlank() || " ".equals(s) || "\n".equals(s) || "null".equals(s)) continue;
                Map<String, Object> row = new HashMap<>();
                row.put("char", s);
                row.put("count", intVal(e.getValue(), 1));
                list.add(row);
            }
            list.sort((a, b) -> Integer.compare(intVal(b.get("count"), 0), intVal(a.get("count"), 0)));
        }
        return list;
    }

    private Map<String, Object> issue(String id, String title, String detail) {
        Map<String, Object> m = new HashMap<>();
        m.put("id", id);
        m.put("title", title);
        m.put("detail", detail);
        return m;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> asMap(Object o) {
        if (o instanceof Map<?, ?> m) return (Map<String, Object>) m;
        return null;
    }

    private static String text(Object v, String def) {
        if (v == null) return def;
        String s = String.valueOf(v).trim();
        return s.isEmpty() ? def : s;
    }

    private static int intVal(Object v, int def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.intValue();
        try {
            return (int) Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }

    private static long longVal(Object v, long def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.longValue();
        try {
            return (long) Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }

    private static double doubleVal(Object v, double def) {
        if (v == null) return def;
        if (v instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(String.valueOf(v));
        } catch (Exception e) {
            return def;
        }
    }
}
