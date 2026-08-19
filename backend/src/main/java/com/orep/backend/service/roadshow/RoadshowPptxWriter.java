package com.orep.backend.service.roadshow;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * 写出可改字的 16:9 pptx。页上是文本框，不是整页图。
 */
public final class RoadshowPptxWriter {

    private RoadshowPptxWriter() {
    }

    public static byte[] write(List<Map<String, Object>> pages) throws IOException {
        if (pages == null || pages.isEmpty()) {
            throw new IllegalArgumentException("没有可做成页的内容");
        }
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            put(zos, "[Content_Types].xml", contentTypes(pages.size()));
            put(zos, "_rels/.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
                    </Relationships>
                    """);
            put(zos, "ppt/presentation.xml", presentation(pages.size()));
            put(zos, "ppt/_rels/presentation.xml.rels", presentationRels(pages.size()));
            put(zos, "ppt/slideLayouts/slideLayout1.xml", LAYOUT);
            put(zos, "ppt/slideLayouts/_rels/slideLayout1.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
                    </Relationships>
                    """);
            put(zos, "ppt/slideMasters/slideMaster1.xml", MASTER);
            put(zos, "ppt/slideMasters/_rels/slideMaster1.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
                      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
                    </Relationships>
                    """);
            put(zos, "ppt/theme/theme1.xml", THEME);
            for (int i = 0; i < pages.size(); i++) {
                put(zos, "ppt/slides/slide" + (i + 1) + ".xml", slideXml(pages.get(i)));
                put(zos, "ppt/slides/_rels/slide" + (i + 1) + ".xml.rels", """
                        <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
                        </Relationships>
                        """);
            }
        }
        return bos.toByteArray();
    }

    static String slideXml(Map<String, Object> page) {
        String kicker = esc(str(page.get("kicker")));
        String title = esc(str(page.get("title")));
        String number = esc(str(page.get("number")));
        String line = esc(str(page.get("line")));
        StringBuilder shapes = new StringBuilder();
        int id = 2;
        shapes.append(textBox(id++, "标签", kicker, 685800, 320000, 10820400, 400000, 1400, "E8B86D", false));
        shapes.append(textBox(id++, "标题", title, 685800, 800000, 10820400, 1400000, number.isBlank() ? 3200 : 2800, "FFFFFF", true));
        if (!number.isBlank()) {
            shapes.append(textBox(id++, "数字", number, 685800, 2400000, 10820400, 1800000, 5400, "E8B86D", true));
        }
        if (!line.isBlank()) {
            long y = number.isBlank() ? 2600000 : 4400000;
            shapes.append(textBox(id++, "一句", line, 685800, y, 10820400, 900000, 1800, "D7DEE8", false));
        }
        if (page.get("blocks") instanceof List<?> blocks) {
            long y = number.isBlank() ? 3700000 : 5400000;
            int i = 0;
            for (Object block : blocks) {
                String text = esc(str(block));
                if (text.isBlank()) continue;
                shapes.append(textBox(id++, "要点" + (i + 1), text,
                        685800 + i * 2000000L, y, 1800000, 600000, 1400, "D7DEE8", false));
                i += 1;
                if (i >= 5) break;
            }
        }
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                  <p:cSld>
                    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="152238"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
                    <p:spTree>
                      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                      <p:grpSpPr/>
                """ + shapes + """
                    </p:spTree>
                  </p:cSld>
                  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
                </p:sld>
                """;
    }

    private static String textBox(int id, String name, String text, long x, long y, long cx, long cy, int sz, String color, boolean bold) {
        return """
                <p:sp>
                  <p:nvSpPr>
                    <p:cNvPr id="%d" name="%s"/>
                    <p:cNvSpPr txBox="1"/>
                    <p:nvPr/>
                  </p:nvSpPr>
                  <p:spPr>
                    <a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                    <a:noFill/>
                  </p:spPr>
                  <p:txBody>
                    <a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/>
                    <a:lstStyle/>
                    <a:p>
                      <a:pPr algn="l"/>
                      <a:r>
                        <a:rPr lang="zh-CN" sz="%d" b="%d" dirty="0">
                          <a:solidFill><a:srgbClr val="%s"/></a:solidFill>
                          <a:latin typeface="Calibri"/><a:ea typeface="Microsoft YaHei"/>
                        </a:rPr>
                        <a:t>%s</a:t>
                      </a:r>
                    </a:p>
                  </p:txBody>
                </p:sp>
                """.formatted(id, name, x, y, cx, cy, sz, bold ? 1 : 0, color, text);
    }

    private static String contentTypes(int n) {
        StringBuilder b = new StringBuilder("""
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                  <Default Extension="xml" ContentType="application/xml"/>
                  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
                  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
                  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
                  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
                """);
        for (int i = 1; i <= n; i++) {
            b.append("  <Override PartName=\"/ppt/slides/slide").append(i)
                    .append(".xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slide+xml\"/>\n");
        }
        b.append("</Types>");
        return b.toString();
    }

    private static String presentation(int n) {
        StringBuilder ids = new StringBuilder();
        for (int i = 1; i <= n; i++) {
            ids.append("<p:sldId id=\"").append(255 + i).append("\" r:id=\"rId").append(i).append("\"/>");
        }
        return """
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                                xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdM"/></p:sldMasterIdLst>
                  <p:sldIdLst>%s</p:sldIdLst>
                  <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
                  <p:notesSz cx="6858000" cy="9144000"/>
                </p:presentation>
                """.formatted(ids);
    }

    private static String presentationRels(int n) {
        StringBuilder b = new StringBuilder("""
                <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                """);
        for (int i = 1; i <= n; i++) {
            b.append("  <Relationship Id=\"rId").append(i)
                    .append("\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide\" Target=\"slides/slide")
                    .append(i).append(".xml\"/>\n");
        }
        b.append("""
                  <Relationship Id="rIdM" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
                  <Relationship Id="rIdT" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
                </Relationships>
                """);
        return b.toString();
    }

    private static String str(Object v) {
        return v == null ? "" : String.valueOf(v);
    }

    static String esc(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
    }

    private static void put(ZipOutputStream zos, String name, String content) throws IOException {
        zos.putNextEntry(new ZipEntry(name));
        zos.write(content.getBytes(StandardCharsets.UTF_8));
        zos.closeEntry();
    }

    private static final String LAYOUT = """
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                         xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                         xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
              <p:cSld name="空白">
                <p:spTree>
                  <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                  <p:grpSpPr/>
                </p:spTree>
              </p:cSld>
              <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
            </p:sldLayout>
            """;

    private static final String MASTER = """
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                         xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                         xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
              <p:cSld>
                <p:bg><p:bgPr><a:solidFill><a:srgbClr val="152238"/></a:solidFill></p:bgPr></p:bg>
                <p:spTree>
                  <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                  <p:grpSpPr/>
                </p:spTree>
              </p:cSld>
              <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"
                        accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"
                        hlink="hlink" folHlink="folHlink"/>
              <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
            </p:sldMaster>
            """;

    private static final String THEME = """
            <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="路演台">
              <a:themeElements>
                <a:clrScheme name="路演台">
                  <a:dk1><a:srgbClr val="152238"/></a:dk1>
                  <a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>
                  <a:dk2><a:srgbClr val="1E3356"/></a:dk2>
                  <a:lt2><a:srgbClr val="F4F1EA"/></a:lt2>
                  <a:accent1><a:srgbClr val="E8B86D"/></a:accent1>
                  <a:accent2><a:srgbClr val="C43A12"/></a:accent2>
                  <a:accent3><a:srgbClr val="059669"/></a:accent3>
                  <a:accent4><a:srgbClr val="2563EB"/></a:accent4>
                  <a:accent5><a:srgbClr val="0891B2"/></a:accent5>
                  <a:accent6><a:srgbClr val="D97706"/></a:accent6>
                  <a:hlink><a:srgbClr val="E8B86D"/></a:hlink>
                  <a:folHlink><a:srgbClr val="C43A12"/></a:folHlink>
                </a:clrScheme>
                <a:fontScheme name="路演台">
                  <a:majorFont><a:latin typeface="Calibri"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface=""/></a:majorFont>
                  <a:minorFont><a:latin typeface="Calibri"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface=""/></a:minorFont>
                </a:fontScheme>
                <a:fmtScheme name="Office">
                  <a:fillStyleLst>
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                  </a:fillStyleLst>
                  <a:lnStyleLst>
                    <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
                    <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
                    <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
                  </a:lnStyleLst>
                  <a:effectStyleLst>
                    <a:effectStyle><a:effectLst/></a:effectStyle>
                    <a:effectStyle><a:effectLst/></a:effectStyle>
                    <a:effectStyle><a:effectLst/></a:effectStyle>
                  </a:effectStyleLst>
                  <a:bgFillStyleLst>
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                    <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
                  </a:bgFillStyleLst>
                </a:fmtScheme>
              </a:themeElements>
            </a:theme>
            """;
}
