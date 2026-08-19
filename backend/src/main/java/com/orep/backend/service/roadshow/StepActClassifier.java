package com.orep.backend.service.roadshow;

import java.util.LinkedHashMap;
import java.util.Map;

public final class StepActClassifier {

    private static final Map<String, String[]> TABLE = new LinkedHashMap<>();

    static {
        TABLE.put("logistics", new String[]{"交给", "下一棒", "回工位", "请回", "谢谢观看", "下一页请看"});
        TABLE.put("demo", new String[]{"演示", "运行程序", "拔掉", "现场", "操作", "联调", "串口"});
        TABLE.put("problem", new String[]{"损耗", "痛点", "问题是", "不足", "误判", "难题"});
        TABLE.put("cause", new String[]{"原因", "断点", "卡在", "因为", "导致"});
        TABLE.put("method", new String[]{"方案", "架构", "五层", "模块", "我们做", "感知层", "总体思路"});
        TABLE.put("evidence", new String[]{"降到", "精度", "对比", "测试", "结果", "0.96", "验收通过"});
        TABLE.put("craft", new String[]{"安全", "规范", "国标", "GB/", "合规", "知识产权"});
        TABLE.put("team", new String[]{"分工", "岗位", "协作", "项目经理", "工程师", "补台"});
        TABLE.put("close", new String[]{"总结", "请评委", "未来规划", "收束"});
        TABLE.put("hook", new String[]{"评委", "大家好", "参赛作品", "汇报"});
    }

    private StepActClassifier() {
    }

    public static String classify(String content, String focus) {
        String hay = (focus == null ? "" : focus) + " " + (content == null ? "" : content);
        String best = "hook";
        int bestScore = 0;
        for (Map.Entry<String, String[]> e : TABLE.entrySet()) {
            int score = 0;
            for (String k : e.getValue()) {
                if (hay.contains(k)) score += 1;
            }
            if (score > bestScore) {
                bestScore = score;
                best = e.getKey();
            }
        }
        if (bestScore == 0) return "hook";
        return best;
    }
}
