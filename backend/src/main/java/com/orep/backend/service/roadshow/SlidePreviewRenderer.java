package com.orep.backend.service.roadshow;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * 从 pptx 拼出这一页的画面：图按位置铺上，字叠上去。给对照用，不是另做一页。
 */
public final class SlidePreviewRenderer {

    static final int WIDTH = 1280;
    static final int HEIGHT = 720;
    private static final long SLIDE_CX = 9144000L;
    private static final long SLIDE_CY = 5143500L;
    private static final Pattern PIC = Pattern.compile("<p:pic[\\s>][\\s\\S]*?</p:pic>");
    private static final Pattern SP = Pattern.compile("<p:sp[\\s>][\\s\\S]*?</p:sp>");
    private static final Pattern PARA = Pattern.compile("<a:p[\\s>][\\s\\S]*?</a:p>");
    private static final Pattern BLIP = Pattern.compile("r:embed=\"(rId[^\"]+)\"");
    private static final Pattern OFF = Pattern.compile("<a:off x=\"(\\d+)\" y=\"(\\d+)\"/>");
    private static final Pattern EXT = Pattern.compile("<a:ext cx=\"(\\d+)\" cy=\"(\\d+)\"/>");
    private static final Pattern REL = Pattern.compile("Id=\"(rId[^\"]+)\"[^>]*Target=\"([^\"]+)\"");
    private static final Pattern TEXT = Pattern.compile("<a:t[^>]*>(.*?)</a:t>", Pattern.DOTALL);
    private static final Pattern SZ = Pattern.compile("sz=\"(\\d+)\"");
    private static final Pattern SRGB = Pattern.compile("<a:srgbClr val=\"([0-9A-Fa-f]{6})\"/>");
    private static final Pattern ALIGN = Pattern.compile("algn=\"(ctr|r|just)\"");
    private static final Font CJK = firstFont();

    private SlidePreviewRenderer() {
    }

    public static byte[] png(Path pptx, int page) throws IOException {
        if (pptx == null || !java.nio.file.Files.isRegularFile(pptx) || page < 1) {
            throw new IOException("没有这一页");
        }
        try (ZipFile zip = new ZipFile(pptx.toFile())) {
            String xml = read(zip, "ppt/slides/slide" + page + ".xml");
            if (xml.isBlank()) throw new IOException("没有这一页");
            String rels = read(zip, "ppt/slides/_rels/slide" + page + ".xml.rels");
            Map<String, String> media = relsOf(rels);
            BufferedImage canvas = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
            Graphics2D g = canvas.createGraphics();
            g.setColor(new Color(0x15, 0x22, 0x38));
            g.fillRect(0, 0, WIDTH, HEIGHT);
            g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
            g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            List<Pic> pics = picsOf(xml, media);
            pics.sort(Comparator.comparingLong(p -> p.cx * p.cy));
            boolean drew = false;
            for (Pic pic : pics) {
                if (drawPic(g, zip, pic)) drew = true;
            }
            drawTexts(g, xml);
            if (!drew && textsOf(xml).isEmpty()) {
                drawFallbackText(g, xml);
            }
            g.dispose();
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            ImageIO.write(canvas, "png", out);
            return out.toByteArray();
        }
    }

    private static boolean drawPic(Graphics2D g, ZipFile zip, Pic pic) {
        String entry = pic.target;
        if (entry.startsWith("../")) entry = "ppt/" + entry.substring(3);
        else if (!entry.startsWith("ppt/")) entry = "ppt/slides/" + entry;
        ZipEntry ze = zip.getEntry(entry);
        if (ze == null) return false;
        try (InputStream in = zip.getInputStream(ze)) {
            BufferedImage img = ImageIO.read(in);
            if (img == null) return false;
            int x = px(pic.x, SLIDE_CX, WIDTH);
            int y = px(pic.y, SLIDE_CY, HEIGHT);
            int w = Math.max(1, px(pic.cx, SLIDE_CX, WIDTH));
            int h = Math.max(1, px(pic.cy, SLIDE_CY, HEIGHT));
            g.drawImage(img, x, y, w, h, null);
            return true;
        } catch (IOException e) {
            return false;
        }
    }

    private static void drawTexts(Graphics2D g, String xml) {
        Matcher sp = SP.matcher(xml);
        while (sp.find()) {
            String chunk = sp.group();
            Matcher off = OFF.matcher(chunk);
            Matcher ext = EXT.matcher(chunk);
            if (!off.find() || !ext.find()) continue;
            int x = px(Long.parseLong(off.group(1)), SLIDE_CX, WIDTH);
            int y = px(Long.parseLong(off.group(2)), SLIDE_CY, HEIGHT);
            int w = Math.max(8, px(Long.parseLong(ext.group(1)), SLIDE_CX, WIDTH));
            int h = Math.max(8, px(Long.parseLong(ext.group(2)), SLIDE_CY, HEIGHT));
            List<String> lines = parasOf(chunk);
            if (lines.isEmpty()) continue;
            int sz = firstInt(SZ, chunk, 1800);
            int fontPx = Math.max(12, Math.min(h, Math.round(sz * 0.0133f)));
            if (lines.size() > 1) fontPx = Math.min(fontPx, Math.max(12, h / (lines.size() + 1)));
            boolean bold = chunk.contains("b=\"1\"") || chunk.contains("b=\"true\"");
            Color color = colorOf(chunk);
            String align = alignOf(chunk);
            g.setColor(color);
            g.setFont(CJK.deriveFont(bold ? Font.BOLD : Font.PLAIN, (float) fontPx));
            FontMetrics fm = g.getFontMetrics();
            int lineH = Math.max(fm.getHeight(), fontPx + 4);
            int ty = y + fm.getAscent() + 2;
            for (String line : lines) {
                if (ty > y + h) break;
                List<String> wrapped = wrap(fm, line, w - 8);
                for (String bit : wrapped) {
                    if (ty > y + h) break;
                    int tx = x + 4;
                    int tw = fm.stringWidth(bit);
                    if ("ctr".equals(align)) tx = x + Math.max(0, (w - tw) / 2);
                    else if ("r".equals(align)) tx = x + Math.max(0, w - tw - 4);
                    g.drawString(bit, tx, ty);
                    ty += lineH;
                }
            }
        }
    }

    private static List<String> parasOf(String chunk) {
        List<String> out = new ArrayList<>();
        Matcher p = PARA.matcher(chunk);
        boolean any = false;
        while (p.find()) {
            any = true;
            StringBuilder line = new StringBuilder();
            Matcher t = TEXT.matcher(p.group());
            while (t.find()) line.append(LegacySlideReader.unescape(t.group(1)));
            String s = line.toString().replace('\n', ' ').trim();
            if (s.isBlank() || LegacySlideReader.junkLine(s)) continue;
            out.add(s);
        }
        if (!any) {
            Matcher t = TEXT.matcher(chunk);
            StringBuilder line = new StringBuilder();
            while (t.find()) line.append(LegacySlideReader.unescape(t.group(1)));
            String s = line.toString().trim();
            if (!s.isBlank() && !LegacySlideReader.junkLine(s)) out.add(s);
        }
        return out;
    }

    private static List<String> wrap(FontMetrics fm, String text, int maxW) {
        List<String> out = new ArrayList<>();
        if (text == null || text.isBlank()) return out;
        if (maxW < 16 || fm.stringWidth(text) <= maxW) {
            out.add(text);
            return out;
        }
        StringBuilder cur = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            cur.append(c);
            if (fm.stringWidth(cur.toString()) > maxW && cur.length() > 1) {
                cur.deleteCharAt(cur.length() - 1);
                out.add(cur.toString());
                cur.setLength(0);
                cur.append(c);
            }
        }
        if (cur.length() > 0) out.add(cur.toString());
        return out;
    }

    private static Color colorOf(String chunk) {
        Matcher m = SRGB.matcher(chunk);
        if (m.find()) {
            try {
                return new Color(Integer.parseInt(m.group(1), 16));
            } catch (NumberFormatException ignored) {
                // fall through
            }
        }
        return Color.WHITE;
    }

    private static String alignOf(String chunk) {
        Matcher m = ALIGN.matcher(chunk);
        return m.find() ? m.group(1) : "l";
    }

    private static int firstInt(Pattern p, String chunk, int fallback) {
        Matcher m = p.matcher(chunk);
        if (!m.find()) return fallback;
        try {
            return Integer.parseInt(m.group(1));
        } catch (NumberFormatException e) {
            return fallback;
        }
    }

    private static Font firstFont() {
        String[] names = {"PingFang SC", "Hiragino Sans GB", "Songti SC", "Heiti SC", "SansSerif"};
        for (String name : names) {
            Font f = new Font(name, Font.PLAIN, 18);
            if (!"Dialog".equals(f.getFamily()) || "SansSerif".equals(name) || "PingFang SC".equals(name)) {
                if (f.canDisplay('番') || "SansSerif".equals(name)) return f;
            }
        }
        return new Font(Font.SANS_SERIF, Font.PLAIN, 18);
    }

    private static void drawFallbackText(Graphics2D g, String xml) {
        g.setColor(Color.WHITE);
        g.setFont(new Font("SansSerif", Font.BOLD, 28));
        int y = 80;
        for (String line : textsOf(xml)) {
            if (y > HEIGHT - 40) break;
            g.drawString(line.length() > 36 ? line.substring(0, 36) : line, 48, y);
            y += 40;
        }
    }

    private static List<String> textsOf(String xml) {
        List<String> out = new ArrayList<>();
        Matcher m = TEXT.matcher(xml);
        while (m.find()) {
            String t = LegacySlideReader.unescape(m.group(1)).trim();
            if (t.isBlank() || LegacySlideReader.junkLine(t) || t.length() > 80) continue;
            out.add(t);
            if (out.size() >= 8) break;
        }
        return out;
    }

    private static List<Pic> picsOf(String xml, Map<String, String> media) {
        List<Pic> out = new ArrayList<>();
        Matcher block = PIC.matcher(xml);
        while (block.find()) {
            String chunk = block.group();
            Matcher b = BLIP.matcher(chunk);
            if (!b.find()) continue;
            String target = media.get(b.group(1));
            if (target == null || target.isBlank()) continue;
            Matcher off = OFF.matcher(chunk);
            Matcher ext = EXT.matcher(chunk);
            long x = 0, y = 0, cx = SLIDE_CX, cy = SLIDE_CY;
            if (off.find()) {
                x = Long.parseLong(off.group(1));
                y = Long.parseLong(off.group(2));
            }
            if (ext.find()) {
                cx = Long.parseLong(ext.group(1));
                cy = Long.parseLong(ext.group(2));
            }
            out.add(new Pic(target, x, y, cx, cy));
        }
        return out;
    }

    private static Map<String, String> relsOf(String rels) {
        Map<String, String> out = new LinkedHashMap<>();
        if (rels == null) return out;
        Matcher m = REL.matcher(rels);
        while (m.find()) out.put(m.group(1), m.group(2));
        return out;
    }

    private static int px(long emu, long slide, int pixels) {
        return (int) Math.round(emu * (double) pixels / slide);
    }

    private static String read(ZipFile zip, String name) throws IOException {
        ZipEntry e = zip.getEntry(name);
        if (e == null) return "";
        try (InputStream in = zip.getInputStream(e)) {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        }
    }

    private record Pic(String target, long x, long y, long cx, long cy) {
    }
}
