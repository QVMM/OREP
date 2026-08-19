package com.orep.backend.service.roadshow;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 逐字稿切段：翻页、PPT 展示、现场。肥段标 fat。
 */
public final class ScriptCueParser {

    private static final Pattern SPEAKER = Pattern.compile("^([\\u4e00-\\u9fffA-Za-z0-9]{2,16})：\\s*(.*)$");
    private static final Pattern FLIP = Pattern.compile("（翻页）|\\(翻页\\)|请翻到下一页");
    private static final Pattern PPT_SHOW = Pattern.compile("PPT\\s*同步展示([^。\\n]{2,40})|PPT展示([^。\\n\\)）]{2,40})|【动作】[^\\n]*PPT[^\\n]{0,40}");
    private static final Pattern LIVE = Pattern.compile("【运行|【拔掉|【现场结果】|打开核心代码|打开环境监测|拔掉了");

    private ScriptCueParser() {
    }

    public static List<Map<String, Object>> parse(String verbatim) {
        List<Map<String, Object>> spans = new ArrayList<>();
        if (verbatim == null || verbatim.isBlank()) return spans;
        String[] lines = verbatim.split("\\R");
        StringBuilder buf = new StringBuilder();
        String speaker = "";
        int fromLine = 1;
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            if (line.isEmpty()) continue;
            Matcher sp = SPEAKER.matcher(line);
            if (sp.matches()) {
                speaker = speakerMerge(speaker, sp.group(1));
                line = sp.group(2).trim();
            }
            buf.append(line).append('\n');
            boolean flip = FLIP.matcher(line).find();
            boolean show = PPT_SHOW.matcher(line).find();
            boolean live = LIVE.matcher(line).find();
            if (flip || show || live || i == lines.length - 1) {
                String text = buf.toString().trim();
                if (!text.isEmpty()) {
                    spans.add(span(spans.size() + 1, fromLine, i + 1, speaker, text, flip, show, live, line));
                }
                buf.setLength(0);
                speaker = "";
                fromLine = i + 2;
            }
        }
        return spans;
    }

    private static String speakerMerge(String cur, String next) {
        if (cur.isEmpty()) return next;
        if (cur.contains(next)) return cur;
        return cur + " / " + next;
    }

    private static Map<String, Object> span(
            int idx, int from, int to, String speaker, String text,
            boolean flip, boolean show, boolean live, String rawLine
    ) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", "sp_" + idx);
        row.put("fromLine", from);
        row.put("toLine", to);
        row.put("speaker", speaker);
        row.put("text", text);
        String cueType = live ? "live" : show ? "ppt_show" : flip ? "flip" : "none";
        row.put("cueType", cueType);
        row.put("cueRaw", rawLine);
        row.put("hold", live);
        int topics = topicHints(text);
        boolean fat = !live && text.replaceAll("\\s+", "").length() > 40 && topics >= 3;
        row.put("fat", fat);
        row.put("topicHints", topics);
        return row;
    }

    static int topicHints(String text) {
        String[] marks = {"规划", "菜园", "工程中心", "政策", "架构", "精度", "时间", "痛点", "传感器", "模型"};
        int n = 0;
        for (String m : marks) {
            if (text.contains(m)) n += 1;
        }
        return n;
    }
}
