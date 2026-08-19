package com.orep.backend.service.roadshow;

import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class SlideTextPatcher {

    private SlideTextPatcher() {
    }

    public static String patch(String xml, List<String> from, List<String> to) {
        if (xml == null) return "";
        if (from == null || to == null) return xml;
        String next = xml;
        int n = Math.min(from.size(), to.size());
        for (int i = 0; i < n; i++) {
            String a = from.get(i) == null ? "" : from.get(i);
            String b = to.get(i) == null ? "" : to.get(i);
            if (a.equals(b) || a.isBlank()) continue;
            next = replaceOnce(next, a, b);
        }
        return next;
    }

    static String replaceOnce(String xml, String from, String to) {
        Pattern p = Pattern.compile("<a:t([^>]*)>" + Pattern.quote(esc(from)) + "</a:t>");
        Matcher m = p.matcher(xml);
        if (m.find()) {
            return m.replaceFirst(Matcher.quoteReplacement("<a:t" + m.group(1) + ">" + esc(to) + "</a:t>"));
        }
        return xml;
    }

    static String esc(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }
}
