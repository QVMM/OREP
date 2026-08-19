package com.orep.backend.service.roadshow;

/**
 * 把讲稿段收成页上能看的标题和一句。不要把角色名前缀和半截口语写上去。
 */
public final class SlideClaim {

    private SlideClaim() {
    }

    public static String title(String act, String spoken) {
        String t = clean(spoken);
        if (t.isBlank()) return fallback(act);
        String book = between(t, '《', '》');
        if (book != null && book.length() >= 4 && book.length() <= 22
                && (book.contains("慧眼") || book.contains("鲜果") || book.contains("番茄") || book.contains("株"))) {
            return clipAtWord(book, 18);
        }
        if (t.contains("六个部分")) return "这场分六个部分";
        if (t.contains("四大痛点")) return "四大痛点";
        if (t.contains("识土") && (t.contains("识图") || t.contains("使谱") || t.contains("识谱"))) {
            return "识土、识图、使谱";
        }
        if (t.contains("核心技能")) return "核心技能";
        if (t.contains("五层") || (t.contains("架构") && t.contains("感知层"))) return "系统架构";
        if (t.contains("规划建议") || t.contains("农业强国") || t.contains("十五五")) return "政策背景";
        if (t.contains("请验收") || t.contains("报告项目经理")) return "采集验收";
        if (t.contains("岗位") || t.contains("项目经理兼") || t.contains("负责团队")) return "岗位分工";
        if (t.contains("知识库") || t.contains("种植知识")) return "种植知识库";
        if (t.contains("菜园") || t.contains("项目的起点")) return "从自家菜园说起";
        if ("problem".equals(act) && t.contains("损耗") && !t.contains("六个部分")) return "损耗发生在入库前";
        if ("demo".equals(act) && (t.contains("传感器") || t.contains("ESP32") || t.contains("核心代码"))) {
            return t.contains("核心代码") ? "采集代码" : "传感器采集";
        }
        if (t.contains("精确度") || t.contains("精度曲线") || t.contains("精度仅")) return "模型精度";
        if (t.contains("成熟度")) return "成熟度识别";
        if (t.contains("区块链") || t.contains("溯源") || t.contains("防篡改")) return "溯源存证";
        if (t.contains("系统功能") || t.contains("驾驶舱")) return "系统功能";
        if (t.contains("创新")) return "创新与成果";
        if (t.contains("未来规划") || t.contains("应用价值")) return "价值与规划";
        if (t.contains("尊敬的") || t.contains("大家好") || t.contains("参赛作品")) return "开场";
        return clipAtWord(t, 16);
    }

    public static String line(String spoken) {
        return clipAtWord(clean(spoken), 28);
    }

    public static String clean(String spoken) {
        if (spoken == null) return "";
        String t = spoken.replace("逐字稿全文", " ").replace("路演讲稿", " ");
        t = t.replaceAll("【[^】]{0,80}】", " ");
        t = t.replaceAll("(?:^|[\\s，。；])[\\u4e00-\\u9fffA-Za-z]{2,12}：\\s*", " ");
        t = t.replaceAll("python复制|async def \\w+\\([^)]*\\)", " ");
        t = t.replaceAll("\\s+", " ").trim();
        return t;
    }

    static String fallback(String act) {
        if ("problem".equals(act)) return "问题";
        if ("method".equals(act)) return "方案";
        if ("demo".equals(act)) return "演示";
        if ("evidence".equals(act)) return "结果";
        if ("team".equals(act)) return "分工";
        if ("close".equals(act)) return "收束";
        return "开场";
    }

    static String clipAtWord(String s, int n) {
        if (s == null) return "";
        String t = s.trim();
        if (t.length() <= n) return t;
        String head = t.substring(0, n);
        int cut = lastBreak(head);
        if (cut >= 8) head = head.substring(0, cut);
        return head.replaceAll("[，。；、,.]+$", "");
    }

    private static int lastBreak(String s) {
        int best = -1;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '，' || c == '。' || c == '；' || c == '、' || c == ' ' || c == ',' || c == '.') best = i;
        }
        return best;
    }

    private static String between(String s, char a, char b) {
        int i = s.indexOf(a);
        int j = s.indexOf(b, i + 1);
        if (i < 0 || j < 0) return null;
        return s.substring(i + 1, j).trim();
    }
}
