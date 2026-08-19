package com.orep.backend.service;

import org.springframework.stereotype.Component;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** 最小可打开空白 OOXML（docx / xlsx / pptx）。 */
@Component
public class OfficeBlankDocumentFactory {

    public byte[] createBlank(String ext) throws IOException {
        return switch (normalizeExt(ext)) {
            case "docx" -> createDocx();
            case "xlsx" -> createXlsx();
            case "pptx" -> createPptx();
            default -> throw new IllegalArgumentException("仅支持新建 docx / xlsx / pptx");
        };
    }

    public static String normalizeExt(String ext) {
        if (ext == null || ext.isBlank()) return "docx";
        String e = ext.trim().toLowerCase();
        return e.startsWith(".") ? e.substring(1) : e;
    }

    private byte[] createDocx() throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            put(zos, "[Content_Types].xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                      <Default Extension="xml" ContentType="application/xml"/>
                      <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
                      <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
                    </Types>
                    """);
            put(zos, "_rels/.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
                    </Relationships>
                    """);
            put(zos, "word/document.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                      <w:body>
                        <w:p><w:r><w:t></w:t></w:r></w:p>
                        <w:sectPr>
                          <w:pgSz w:w="11906" w:h="16838"/>
                          <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
                        </w:sectPr>
                      </w:body>
                    </w:document>
                    """);
            // 默认开启修订：后续编辑会以 w:ins/w:del 记入作者与时间
            put(zos, "word/settings.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                      <w:trackRevisions/>
                    </w:settings>
                    """);
            put(zos, "word/_rels/document.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
                    </Relationships>
                    """);
        }
        return bos.toByteArray();
    }

    private byte[] createXlsx() throws IOException {
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            put(zos, "[Content_Types].xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                      <Default Extension="xml" ContentType="application/xml"/>
                      <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
                      <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
                      <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
                    </Types>
                    """);
            put(zos, "_rels/.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
                    </Relationships>
                    """);
            put(zos, "xl/workbook.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
                              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
                      <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
                    </workbook>
                    """);
            put(zos, "xl/_rels/workbook.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
                      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
                    </Relationships>
                    """);
            put(zos, "xl/worksheets/sheet1.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>
                    """);
            put(zos, "xl/styles.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
                      <fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>
                      <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
                      <borders count="1"><border/></borders>
                      <cellStyleXfs count="1"><xf/></cellStyleXfs>
                      <cellXfs count="1"><xf/></cellXfs>
                    </styleSheet>
                    """);
        }
        return bos.toByteArray();
    }

    private byte[] createPptx() throws IOException {
        // 16:9 标题页 + 正文占位，便于协同时直接开写（空白页在 Impress 里体验差）
        // EMU: 12192000 x 6858000 = 13.333" x 7.5" (16:9)
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try (ZipOutputStream zos = new ZipOutputStream(bos)) {
            put(zos, "[Content_Types].xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                      <Default Extension="xml" ContentType="application/xml"/>
                      <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
                      <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
                      <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
                      <Override PartName="/ppt/slideLayouts/slideLayout2.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
                      <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
                      <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
                    </Types>
                    """);
            put(zos, "_rels/.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
                    </Relationships>
                    """);
            put(zos, "ppt/presentation.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                                    xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                                    xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                      <p:sldMasterIdLst>
                        <p:sldMasterId id="2147483648" r:id="rId2"/>
                      </p:sldMasterIdLst>
                      <p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>
                      <p:sldSz cx="12192000" cy="6858000" type="screen16x9"/>
                      <p:notesSz cx="6858000" cy="9144000"/>
                    </p:presentation>
                    """);
            put(zos, "ppt/_rels/presentation.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
                      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
                      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
                    </Relationships>
                    """);
            // 标题页：居中标题 + 副标题，协同打开即可直接改字
            put(zos, "ppt/slides/slide1.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                           xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                           xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                      <p:cSld>
                        <p:spTree>
                          <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                          <p:grpSpPr/>
                          <p:sp>
                            <p:nvSpPr>
                              <p:cNvPr id="2" name="标题"/>
                              <p:cNvSpPr txBox="1"/>
                              <p:nvPr><p:ph type="ctrTitle"/></p:nvPr>
                            </p:nvSpPr>
                            <p:spPr>
                              <a:xfrm>
                                <a:off x="914400" y="2057400"/>
                                <a:ext cx="10363200" cy="1371600"/>
                              </a:xfrm>
                            </p:spPr>
                            <p:txBody>
                              <a:bodyPr anchor="ctr"/>
                              <a:lstStyle/>
                              <a:p>
                                <a:pPr algn="ctr"/>
                                <a:r>
                                  <a:rPr lang="zh-CN" sz="4000" b="1" dirty="0">
                                    <a:solidFill><a:srgbClr val="1F2937"/></a:solidFill>
                                    <a:latin typeface="Calibri"/><a:ea typeface="Microsoft YaHei"/>
                                  </a:rPr>
                                  <a:t>点击编辑标题</a:t>
                                </a:r>
                              </a:p>
                            </p:txBody>
                          </p:sp>
                          <p:sp>
                            <p:nvSpPr>
                              <p:cNvPr id="3" name="副标题"/>
                              <p:cNvSpPr txBox="1"/>
                              <p:nvPr><p:ph type="subTitle" idx="1"/></p:nvPr>
                            </p:nvSpPr>
                            <p:spPr>
                              <a:xfrm>
                                <a:off x="1371600" y="3657600"/>
                                <a:ext cx="9448800" cy="914400"/>
                              </a:xfrm>
                            </p:spPr>
                            <p:txBody>
                              <a:bodyPr anchor="t"/>
                              <a:lstStyle/>
                              <a:p>
                                <a:pPr algn="ctr"/>
                                <a:r>
                                  <a:rPr lang="zh-CN" sz="1800" dirty="0">
                                    <a:solidFill><a:srgbClr val="6B7280"/></a:solidFill>
                                    <a:latin typeface="Calibri"/><a:ea typeface="Microsoft YaHei"/>
                                  </a:rPr>
                                  <a:t>副标题 · 团队协同编辑</a:t>
                                </a:r>
                              </a:p>
                            </p:txBody>
                          </p:sp>
                        </p:spTree>
                      </p:cSld>
                      <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
                    </p:sld>
                    """);
            put(zos, "ppt/slides/_rels/slide1.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
                    </Relationships>
                    """);
            // 标题版式
            put(zos, "ppt/slideLayouts/slideLayout1.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                                 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                                 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="title" preserve="1">
                      <p:cSld name="标题幻灯片">
                        <p:spTree>
                          <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                          <p:grpSpPr/>
                          <p:sp>
                            <p:nvSpPr>
                              <p:cNvPr id="2" name="标题占位符"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
                              <p:nvPr><p:ph type="ctrTitle"/></p:nvPr>
                            </p:nvSpPr>
                            <p:spPr>
                              <a:xfrm><a:off x="914400" y="2057400"/><a:ext cx="10363200" cy="1371600"/></a:xfrm>
                            </p:spPr>
                            <p:txBody><a:bodyPr anchor="ctr"/><a:lstStyle/><a:p><a:endParaRPr lang="zh-CN"/></a:p></p:txBody>
                          </p:sp>
                          <p:sp>
                            <p:nvSpPr>
                              <p:cNvPr id="3" name="副标题占位符"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
                              <p:nvPr><p:ph type="subTitle" idx="1"/></p:nvPr>
                            </p:nvSpPr>
                            <p:spPr>
                              <a:xfrm><a:off x="1371600" y="3657600"/><a:ext cx="9448800" cy="914400"/></a:xfrm>
                            </p:spPr>
                            <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="zh-CN"/></a:p></p:txBody>
                          </p:sp>
                        </p:spTree>
                      </p:cSld>
                      <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
                    </p:sldLayout>
                    """);
            put(zos, "ppt/slideLayouts/_rels/slideLayout1.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
                    </Relationships>
                    """);
            // 标题+正文版式：新建幻灯片时可用
            put(zos, "ppt/slideLayouts/slideLayout2.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                                 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                                 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="obj" preserve="1">
                      <p:cSld name="标题和内容">
                        <p:spTree>
                          <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                          <p:grpSpPr/>
                          <p:sp>
                            <p:nvSpPr>
                              <p:cNvPr id="2" name="标题占位符"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
                              <p:nvPr><p:ph type="title"/></p:nvPr>
                            </p:nvSpPr>
                            <p:spPr>
                              <a:xfrm><a:off x="685800" y="274320"/><a:ext cx="10820400" cy="1143000"/></a:xfrm>
                            </p:spPr>
                            <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="zh-CN"/></a:p></p:txBody>
                          </p:sp>
                          <p:sp>
                            <p:nvSpPr>
                              <p:cNvPr id="3" name="内容占位符"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>
                              <p:nvPr><p:ph idx="1"/></p:nvPr>
                            </p:nvSpPr>
                            <p:spPr>
                              <a:xfrm><a:off x="685800" y="1600200"/><a:ext cx="10820400" cy="4526280"/></a:xfrm>
                            </p:spPr>
                            <p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:endParaRPr lang="zh-CN"/></a:p></p:txBody>
                          </p:sp>
                        </p:spTree>
                      </p:cSld>
                      <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
                    </p:sldLayout>
                    """);
            put(zos, "ppt/slideLayouts/_rels/slideLayout2.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
                    </Relationships>
                    """);
            put(zos, "ppt/slideMasters/slideMaster1.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                                 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                                 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                      <p:cSld>
                        <p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>
                        <p:spTree>
                          <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
                          <p:grpSpPr/>
                        </p:spTree>
                      </p:cSld>
                      <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"
                                accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6"
                                hlink="hlink" folHlink="folHlink"/>
                      <p:sldLayoutIdLst>
                        <p:sldLayoutId id="2147483649" r:id="rId1"/>
                        <p:sldLayoutId id="2147483650" r:id="rId3"/>
                      </p:sldLayoutIdLst>
                    </p:sldMaster>
                    """);
            put(zos, "ppt/slideMasters/_rels/slideMaster1.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
                      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
                      <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout2.xml"/>
                    </Relationships>
                    """);
            put(zos, "ppt/theme/theme1.xml", """
                    <?xml version="1.0" encoding="UTF-8" standalone="yes"?>
                    <a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="启发 Office">
                      <a:themeElements>
                        <a:clrScheme name="启发">
                          <a:dk1><a:sysClr val="windowText" lastClr="111827"/></a:dk1>
                          <a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>
                          <a:dk2><a:srgbClr val="1F2937"/></a:dk2>
                          <a:lt2><a:srgbClr val="F3F4F6"/></a:lt2>
                          <a:accent1><a:srgbClr val="E5481D"/></a:accent1>
                          <a:accent2><a:srgbClr val="2563EB"/></a:accent2>
                          <a:accent3><a:srgbClr val="059669"/></a:accent3>
                          <a:accent4><a:srgbClr val="7C3AED"/></a:accent4>
                          <a:accent5><a:srgbClr val="0891B2"/></a:accent5>
                          <a:accent6><a:srgbClr val="D97706"/></a:accent6>
                          <a:hlink><a:srgbClr val="2563EB"/></a:hlink>
                          <a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink>
                        </a:clrScheme>
                        <a:fontScheme name="启发">
                          <a:majorFont>
                            <a:latin typeface="Calibri"/>
                            <a:ea typeface="Microsoft YaHei"/>
                            <a:cs typeface=""/>
                          </a:majorFont>
                          <a:minorFont>
                            <a:latin typeface="Calibri"/>
                            <a:ea typeface="Microsoft YaHei"/>
                            <a:cs typeface=""/>
                          </a:minorFont>
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
                    """);
        }
        return bos.toByteArray();
    }

    private static void put(ZipOutputStream zos, String name, String content) throws IOException {
        zos.putNextEntry(new ZipEntry(name));
        zos.write(content.getBytes(StandardCharsets.UTF_8));
        zos.closeEntry();
    }
}
