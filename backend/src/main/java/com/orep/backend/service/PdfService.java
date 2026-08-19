package com.orep.backend.service;

import com.orep.backend.dto.ScoreResultVO;
import com.orep.backend.entity.*;
import com.lowagie.text.*;
import com.lowagie.text.Font;
import com.lowagie.text.pdf.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;

@Service
public class PdfService {

    public byte[] generateScoreReport(ScoreResultVO result) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        Document document = new Document(PageSize.A4);
        PdfWriter.getInstance(document, baos);
        document.open();

        BaseFont bfChinese = createChineseBaseFont();

        Font titleFont = new Font(bfChinese, 18, Font.BOLD);
        Font headerFont = new Font(bfChinese, 12, Font.BOLD);
        Font normalFont = new Font(bfChinese, 10, Font.NORMAL);
        Font smallFont = new Font(bfChinese, 9, Font.NORMAL);

        // 标题
        Paragraph title = new Paragraph("路演评审评分报告", titleFont);
        title.setAlignment(Element.ALIGN_CENTER);
        title.setSpacingAfter(20);
        document.add(title);

        // 会议信息
        Paragraph meetingInfo = new Paragraph("会议: " + result.getMeetingTitle(), headerFont);
        meetingInfo.setSpacingAfter(10);
        document.add(meetingInfo);

        // 逐个评分人输出
        for (ScoreResultVO.ScoreRecordVO record : result.getRecords()) {
            // 评分人信息
            Paragraph scorerTitle = new Paragraph(
                    "评分人: " + record.getUsername() + " (" + record.getRole() + ")  总分: " + record.getTotalScore(),
                    headerFont
            );
            scorerTitle.setSpacingBefore(15);
            scorerTitle.setSpacingAfter(8);
            document.add(scorerTitle);

            // 评分详情表格
            PdfPTable table = new PdfPTable(5);
            table.setWidthPercentage(100);
            table.setWidths(new float[]{2, 2, 1.5f, 1, 3.5f});

            // 表头
            addTableHeader(table, "类别", bfChinese);
            addTableHeader(table, "评分项", bfChinese);
            addTableHeader(table, "满分", bfChinese);
            addTableHeader(table, "得分", bfChinese);
            addTableHeader(table, "评语", bfChinese);

            for (ScoreResultVO.ScoreDetailVO detail : record.getDetails()) {
                addTableCell(table, detail.getCategory() != null ? detail.getCategory() : "-", smallFont);
                addTableCell(table, detail.getItemName() != null ? detail.getItemName() : "-", smallFont);
                addTableCell(table, detail.getMaxScore() != null ? detail.getMaxScore().toString() : "-", smallFont);
                addTableCell(table, detail.getScore() != null ? detail.getScore().toString() : "-", smallFont);
                addTableCell(table, detail.getComment() != null ? detail.getComment() : "-", smallFont);
            }

            document.add(table);
        }

        document.close();
        return baos.toByteArray();
    }

    /**
     * 生成讲稿 PDF
     */
    public byte[] generateScriptPdf(Script script) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        Document document = new Document(PageSize.A4, 50, 50, 50, 50);
        PdfWriter.getInstance(document, baos);
        document.open();

        BaseFont bfChinese = createChineseBaseFont();

        Font titleFont = new Font(bfChinese, 22, Font.BOLD, new Color(33, 37, 41));
        Font chapterFont = new Font(bfChinese, 16, Font.BOLD, new Color(0, 102, 204));
        Font stepRoleFont = new Font(bfChinese, 12, Font.BOLD, new Color(51, 51, 51));
        Font stepFocusFont = new Font(bfChinese, 11, Font.ITALIC, new Color(102, 102, 102));
        Font normalFont = new Font(bfChinese, 10, Font.NORMAL, new Color(33, 33, 33));
        Font labelFont = new Font(bfChinese, 10, Font.BOLD, new Color(80, 80, 80));
        Font smallFont = new Font(bfChinese, 9, Font.NORMAL, new Color(120, 120, 120));
        Font transitionFont = new Font(bfChinese, 10, Font.ITALIC, new Color(0, 128, 0));

        ObjectMapper mapper = new ObjectMapper();

        // 封面
        Paragraph title = new Paragraph(script.getTitle() != null ? script.getTitle() : "路演讲稿", titleFont);
        title.setAlignment(Element.ALIGN_CENTER);
        title.setSpacingAfter(30);
        document.add(title);

        // 时间线摘要
        PdfPTable summaryTable = new PdfPTable(4);
        summaryTable.setWidthPercentage(100);
        summaryTable.setWidths(new float[]{2, 3, 1.5f, 1.5f});
        addTableHeader(summaryTable, "章节", bfChinese);
        addTableHeader(summaryTable, "步骤", bfChinese);
        addTableHeader(summaryTable, "主讲人", bfChinese);
        addTableHeader(summaryTable, "时长", bfChinese);

        try {
            if (script.getContent() != null) {
                JsonNode chapters = mapper.readTree(script.getContent());
                int totalMinutes = 0;
                for (JsonNode chapter : chapters) {
                    String chTitle = chapter.has("title") ? chapter.get("title").asText() : "";
                    JsonNode steps = chapter.has("steps") ? chapter.get("steps") : mapper.createArrayNode();
                    int chDuration = chapter.has("totalDuration") ? chapter.get("totalDuration").asInt() : 0;
                    totalMinutes += chDuration;

                    StringBuilder stepNames = new StringBuilder();
                    StringBuilder roles = new StringBuilder();
                    for (JsonNode step : steps) {
                        if (stepNames.length() > 0) stepNames.append(" → ");
                        stepNames.append(step.has("focus") ? step.get("focus").asText() : "");
                        if (roles.length() > 0) roles.append(" → ");
                        roles.append(step.has("role") ? step.get("role").asText() : "");
                    }

                    addTableCell(summaryTable, chTitle, normalFont);
                    addTableCell(summaryTable, stepNames.toString(), smallFont);
                    addTableCell(summaryTable, roles.toString(), smallFont);
                    addTableCell(summaryTable, chDuration + " min", normalFont);
                }
                document.add(summaryTable);

                // 总时长
                Paragraph total = new Paragraph("\n总计时长: " + totalMinutes + " 分钟", labelFont);
                total.setSpacingBefore(10);
                total.setSpacingAfter(20);
                document.add(total);
            }
        } catch (Exception e) {
            // 解析失败时跳过摘要
        }

        // 分页
        document.newPage();

        // 逐章节输出详细内容
        try {
            if (script.getContent() != null) {
                JsonNode chapters = mapper.readTree(script.getContent());
                int chIndex = 0;
                for (JsonNode chapter : chapters) {
                    chIndex++;
                    String chTitle = chapter.has("title") ? chapter.get("title").asText() : "第" + chIndex + "章";
                    int chDuration = chapter.has("totalDuration") ? chapter.get("totalDuration").asInt() : 0;

                    // 章节标题
                    Paragraph chapterP = new Paragraph(chTitle + "  (" + chDuration + " min)", chapterFont);
                    chapterP.setSpacingBefore(15);
                    chapterP.setSpacingAfter(10);
                    document.add(chapterP);

                    // 分隔线
                    PdfPTable line = new PdfPTable(1);
                    line.setWidthPercentage(100);
                    PdfPCell lineCell = new PdfPCell();
                    lineCell.setBorderWidthBottom(1.5f);
                    lineCell.setBorderColorBottom(new Color(0, 102, 204));
                    lineCell.setFixedHeight(2);
                    lineCell.setBorder(0);
                    lineCell.setBorder(Rectangle.BOTTOM);
                    line.addCell(lineCell);
                    document.add(line);

                    JsonNode steps = chapter.has("steps") ? chapter.get("steps") : mapper.createArrayNode();
                    for (JsonNode step : steps) {
                        String role = step.has("role") ? step.get("role").asText() : "";
                        String duration = step.has("duration") ? step.get("duration").asText() + " min" : "";
                        String focus = step.has("focus") ? step.get("focus").asText() : "";
                        String content = step.has("content") ? stripHtml(step.get("content").asText()) : "";
                        String notes = step.has("notes") ? step.get("notes").asText() : "";
                        String transition = step.has("transition") ? step.get("transition").asText() : "";

                        // 角色行
                        Paragraph roleP = new Paragraph();
                        roleP.add(new Chunk("【" + role + "】", stepRoleFont));
                        if (!focus.isEmpty()) {
                            roleP.add(new Chunk("  " + focus, stepFocusFont));
                        }
                        if (!duration.isEmpty()) {
                            roleP.add(new Chunk("  ⏱ " + duration, smallFont));
                        }
                        roleP.setSpacingBefore(10);
                        roleP.setSpacingAfter(3);
                        document.add(roleP);

                        // 内容
                        if (!content.isEmpty()) {
                            Paragraph contentP = new Paragraph(content, normalFont);
                            contentP.setIndentationLeft(20);
                            contentP.setSpacingAfter(3);
                            document.add(contentP);
                        }

                        // 演示提示
                        if (!notes.isEmpty()) {
                            Paragraph notesP = new Paragraph("💡 提示: " + notes, smallFont);
                            notesP.setIndentationLeft(20);
                            notesP.setSpacingAfter(3);
                            document.add(notesP);
                        }

                        // 转场
                        if (!transition.isEmpty()) {
                            Paragraph transP = new Paragraph("↪ 转场: " + transition, transitionFont);
                            transP.setIndentationLeft(20);
                            transP.setSpacingAfter(5);
                            document.add(transP);
                        }
                    }
                }
            }
        } catch (Exception e) {
            document.add(new Paragraph("讲稿内容解析失败: " + e.getMessage(), normalFont));
        }

        // 尾页
        document.newPage();
        Paragraph footer = new Paragraph("— 讲稿终 —", titleFont);
        footer.setAlignment(Element.ALIGN_CENTER);
        footer.setSpacingBefore(200);
        document.add(footer);

        document.close();
        return baos.toByteArray();
    }

    /** 去除 HTML 标签 */
    private String stripHtml(String html) {
        if (html == null) return "";
        return html.replaceAll("<[^>]+>", "").replaceAll("&nbsp;", " ").trim();
    }

    private void addTableHeader(PdfPTable table, String text, BaseFont bf) {
        Font font = new Font(bf, 10, Font.BOLD, Color.WHITE);
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setBackgroundColor(new Color(51, 122, 183));
        cell.setHorizontalAlignment(Element.ALIGN_CENTER);
        cell.setPadding(5);
        table.addCell(cell);
    }

    private void addTableCell(PdfPTable table, String text, Font font) {
        PdfPCell cell = new PdfPCell(new Phrase(text, font));
        cell.setPadding(4);
        table.addCell(cell);
    }

    /** 生成问题报告 PDF */
    public byte[] generateIssueReport(String meetingTitle, List<Issue> issues) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        Document doc = new Document(PageSize.A4, 50, 50, 50, 50);
        PdfWriter.getInstance(doc, baos);
        doc.open();

        BaseFont bf = createChineseBaseFont();

        // 标题
        Font titleFont = new Font(bf, 20, Font.BOLD, new Color(51, 51, 51));
        Paragraph title = new Paragraph("问题报告", titleFont);
        title.setAlignment(Element.ALIGN_CENTER);
        title.setSpacingAfter(8);
        doc.add(title);

        // 会议信息
        Font subFont = new Font(bf, 11, Font.NORMAL, new Color(120, 120, 120));
        Paragraph sub = new Paragraph("会议: " + meetingTitle + "    生成时间: " +
                new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm").format(new java.util.Date()), subFont);
        sub.setAlignment(Element.ALIGN_CENTER);
        sub.setSpacingAfter(20);
        doc.add(sub);

        // 统计
        long resolved = issues.stream().filter(i -> i.getStatus() != null && i.getStatus() == 1).count();
        long unresolved = issues.size() - resolved;

        Font statFont = new Font(bf, 11, Font.NORMAL, new Color(51, 51, 51));
        Paragraph stat = new Paragraph("共计 " + issues.size() + " 项问题  |  已解决 " + resolved + " 项  |  待解决 " + unresolved + " 项", statFont);
        stat.setSpacingAfter(16);
        doc.add(stat);

        if (!issues.isEmpty()) {
            doc.add(Chunk.NEWLINE);

            // 表格
            PdfPTable table = new PdfPTable(4);
            table.setWidthPercentage(100);
            table.setWidths(new float[]{1, 1.5f, 4.5f, 2});

            Font headerFont = new Font(bf, 10, Font.BOLD, Color.WHITE);
            String[] headers = {"序号", "状态", "问题描述", "分类"};
            for (String h : headers) {
                PdfPCell cell = new PdfPCell(new Phrase(h, headerFont));
                cell.setBackgroundColor(new Color(51, 122, 183));
                cell.setHorizontalAlignment(Element.ALIGN_CENTER);
                cell.setPadding(6);
                table.addCell(cell);
            }

            Font cellFont = new Font(bf, 9, Font.NORMAL, new Color(51, 51, 51));
            for (int i = 0; i < issues.size(); i++) {
                Issue issue = issues.get(i);
                addTableCell(table, String.valueOf(i + 1), cellFont);
                addTableCell(table, issue.getStatus() != null && issue.getStatus() == 1 ? "已解决" : "待解决", cellFont);
                addTableCell(table, issue.getDescription() != null ? issue.getDescription() : "-", cellFont);
                addTableCell(table, issue.getCategory() != null ? issue.getCategory() : "-", cellFont);
            }

            doc.add(table);
        } else {
            Font emptyFont = new Font(bf, 12, Font.ITALIC, new Color(180, 180, 180));
            Paragraph empty = new Paragraph("本次会议暂无问题记录", emptyFont);
            empty.setAlignment(Element.ALIGN_CENTER);
            empty.setSpacingBefore(40);
            doc.add(empty);
        }

        doc.close();
        return baos.toByteArray();
    }

    public byte[] generateCertificatePdf(
            String title,
            String awardLevel,
            String description,
            String issuerName,
            String certificateNo,
            String issuedAtText,
            List<String> recipientNames
    ) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        // 横向 A4，内边距预留给装饰边框
        Document document = new Document(PageSize.A4.rotate(), 48, 48, 40, 40);
        PdfWriter writer = PdfWriter.getInstance(document, baos);
        document.open();

        BaseFont bfChinese;
        try {
            bfChinese = createChineseBaseFont();
        } catch (IOException ex) {
            throw new IOException("未找到可嵌入中文字体，无法生成奖状 PDF", ex);
        }

        Color orange = new Color(232, 74, 28);
        Color ink = new Color(109, 43, 24);
        Color muted = new Color(127, 87, 74);
        Color faint = new Color(155, 118, 106);
        Color cream = new Color(255, 250, 247);

        PdfContentByte canvas = writer.getDirectContentUnder();
        Rectangle page = document.getPageSize();
        float left = page.getLeft() + 28;
        float right = page.getRight() - 28;
        float bottom = page.getBottom() + 24;
        float top = page.getTop() - 24;

        // 奶油底色
        canvas.saveState();
        canvas.setColorFill(cream);
        canvas.rectangle(page.getLeft(), page.getBottom(), page.getWidth(), page.getHeight());
        canvas.fill();
        // 外框
        canvas.setColorStroke(new Color(232, 74, 28, 160));
        canvas.setLineWidth(2.2f);
        canvas.rectangle(left, bottom, right - left, top - bottom);
        canvas.stroke();
        // 内框
        canvas.setColorStroke(new Color(232, 74, 28, 70));
        canvas.setLineWidth(0.9f);
        canvas.rectangle(left + 10, bottom + 10, right - left - 20, top - bottom - 20);
        canvas.stroke();
        // 虚线框
        canvas.setColorStroke(new Color(232, 74, 28, 55));
        canvas.setLineWidth(0.7f);
        canvas.setLineDash(5f, 4f, 0f);
        canvas.rectangle(left + 18, bottom + 18, right - left - 36, top - bottom - 36);
        canvas.stroke();
        canvas.restoreState();

        // 右下角印章
        float sealCx = right - 72;
        float sealCy = bottom + 78;
        canvas.saveState();
        canvas.setColorStroke(new Color(196, 58, 18, 140));
        canvas.setLineWidth(2.4f);
        canvas.circle(sealCx, sealCy, 34);
        canvas.stroke();
        canvas.setLineWidth(1.1f);
        canvas.setColorStroke(new Color(196, 58, 18, 60));
        canvas.circle(sealCx, sealCy, 27);
        canvas.stroke();
        canvas.restoreState();

        Font brandFont = new Font(bfChinese, 13, Font.BOLD, orange);
        Font headingFont = new Font(bfChinese, 30, Font.BOLD, ink);
        Font awardTitleFont = new Font(bfChinese, 22, Font.BOLD, orange);
        Font levelFont = new Font(bfChinese, 13, Font.BOLD, new Color(154, 74, 31));
        Font bodyFont = new Font(bfChinese, 12, Font.NORMAL, muted);
        Font grantFont = new Font(bfChinese, 13, Font.NORMAL, muted);
        Font grantNameFont = new Font(bfChinese, 14, Font.BOLD, ink);
        Font metaLabelFont = new Font(bfChinese, 10, Font.NORMAL, faint);
        Font metaValueFont = new Font(bfChinese, 12, Font.BOLD, ink);
        Font sealFont = new Font(bfChinese, 12, Font.BOLD, new Color(196, 58, 18, 160));
        Font noFont = new Font(bfChinese, 9, Font.NORMAL, faint);

        // 品牌行
        PdfPTable brand = new PdfPTable(new float[]{1, 5});
        brand.setWidthPercentage(26);
        brand.setHorizontalAlignment(Element.ALIGN_CENTER);
        brand.getDefaultCell().setBorder(Rectangle.NO_BORDER);
        brand.getDefaultCell().setVerticalAlignment(Element.ALIGN_MIDDLE);
        try (InputStream logoStream = PdfService.class.getResourceAsStream("/brand/competition-brain-mark.png")) {
            if (logoStream != null) {
                Image logo = Image.getInstance(logoStream.readAllBytes());
                logo.scaleToFit(22, 22);
                PdfPCell logoCell = new PdfPCell(logo, false);
                logoCell.setBorder(Rectangle.NO_BORDER);
                logoCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
                logoCell.setVerticalAlignment(Element.ALIGN_MIDDLE);
                logoCell.setPaddingRight(6);
                brand.addCell(logoCell);
            } else {
                brand.addCell("");
            }
        }
        PdfPCell brandName = new PdfPCell(new Phrase("竞赛大脑", brandFont));
        brandName.setBorder(Rectangle.NO_BORDER);
        brandName.setVerticalAlignment(Element.ALIGN_MIDDLE);
        brandName.setPadding(0);
        brand.addCell(brandName);
        brand.setSpacingBefore(12);
        brand.setSpacingAfter(4);
        document.add(brand);

        Paragraph certNo = new Paragraph("编号 " + displayCertificateNo(certificateNo), noFont);
        certNo.setAlignment(Element.ALIGN_CENTER);
        certNo.setSpacingAfter(10);
        document.add(certNo);

        Paragraph heading = new Paragraph("奖 状", headingFont);
        heading.setAlignment(Element.ALIGN_CENTER);
        heading.setSpacingAfter(14);
        document.add(heading);

        String recipients = recipientNames == null || recipientNames.isEmpty()
                ? "获奖者"
                : String.join("、", recipientNames);
        Paragraph grant = new Paragraph();
        grant.setAlignment(Element.ALIGN_CENTER);
        grant.add(new Chunk("兹授予  ", grantFont));
        grant.add(new Chunk(recipients, grantNameFont));
        grant.setSpacingAfter(10);
        document.add(grant);

        Paragraph titleParagraph = new Paragraph(
                title == null || title.isBlank() ? "荣誉奖状" : title,
                awardTitleFont
        );
        titleParagraph.setAlignment(Element.ALIGN_CENTER);
        titleParagraph.setSpacingAfter(8);
        document.add(titleParagraph);

        if (awardLevel != null && !awardLevel.isBlank()) {
            Paragraph level = new Paragraph(awardLevel, levelFont);
            level.setAlignment(Element.ALIGN_CENTER);
            level.setSpacingAfter(12);
            document.add(level);
        }

        String bodyText = (description == null || description.isBlank())
                ? "表彰在本次备赛过程中表现突出的个人或团队，特发此状，以资鼓励。"
                : description;
        Paragraph desc = new Paragraph(bodyText, bodyFont);
        desc.setAlignment(Element.ALIGN_CENTER);
        desc.setLeading(20f);
        desc.setIndentationLeft(48);
        desc.setIndentationRight(48);
        desc.setSpacingAfter(28);
        document.add(desc);

        // 颁发单位 / 日期
        PdfPTable meta = new PdfPTable(2);
        meta.setWidthPercentage(70);
        meta.setHorizontalAlignment(Element.ALIGN_CENTER);
        meta.getDefaultCell().setBorder(Rectangle.NO_BORDER);
        meta.getDefaultCell().setPadding(4);

        PdfPCell issuerLabel = new PdfPCell(new Phrase("颁发单位", metaLabelFont));
        issuerLabel.setBorder(Rectangle.NO_BORDER);
        issuerLabel.setHorizontalAlignment(Element.ALIGN_LEFT);
        meta.addCell(issuerLabel);

        PdfPCell dateLabel = new PdfPCell(new Phrase("颁发日期", metaLabelFont));
        dateLabel.setBorder(Rectangle.NO_BORDER);
        dateLabel.setHorizontalAlignment(Element.ALIGN_RIGHT);
        meta.addCell(dateLabel);

        PdfPCell issuerVal = new PdfPCell(new Phrase(
                issuerName == null || issuerName.isBlank() ? "启发·竞赛大脑" : issuerName,
                metaValueFont
        ));
        issuerVal.setBorder(Rectangle.NO_BORDER);
        issuerVal.setHorizontalAlignment(Element.ALIGN_LEFT);
        meta.addCell(issuerVal);

        PdfPCell dateVal = new PdfPCell(new Phrase(
                issuedAtText == null || issuedAtText.isBlank() ? "—" : issuedAtText,
                metaValueFont
        ));
        dateVal.setBorder(Rectangle.NO_BORDER);
        dateVal.setHorizontalAlignment(Element.ALIGN_RIGHT);
        meta.addCell(dateVal);
        document.add(meta);

        // 印章文字（叠在右下角圆环中心）
        String sealText = (awardLevel != null && !awardLevel.isBlank())
                ? awardLevel.trim().substring(0, Math.min(2, awardLevel.trim().length()))
                : "荣誉";
        ColumnText.showTextAligned(
                writer.getDirectContent(),
                Element.ALIGN_CENTER,
                new Phrase(sealText, sealFont),
                sealCx,
                sealCy - 4,
                -12
        );

        document.close();
        return baos.toByteArray();
    }

    private String displayCertificateNo(String certificateNo) {
        if (certificateNo == null || certificateNo.isBlank()) return "—";
        return certificateNo.replaceFirst("(?i)^OREP-", "");
    }

    private BaseFont createChineseBaseFont() throws IOException {
        List<String> candidates = new ArrayList<>();
        String override = System.getenv("OREP_PDF_FONT_PATH");
        if (override != null && !override.isBlank()) {
            candidates.add(override);
        }
        candidates.add("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc");
        candidates.add("/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf");
        candidates.add("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc");
        candidates.add("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc");
        candidates.add("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc");
        candidates.add("/System/Library/Fonts/STHeiti Light.ttc");
        candidates.add("/System/Library/Fonts/PingFang.ttc");
        candidates.add("/System/Library/Fonts/Supplemental/Songti.ttc");
        candidates.add("/Library/Fonts/Arial Unicode.ttf");
        candidates.add("C:/Windows/Fonts/msyh.ttc");
        candidates.add("C:/Windows/Fonts/simsun.ttc");

        for (String candidate : candidates) {
            if (candidate == null || candidate.isBlank()) {
                continue;
            }
            File fontFile = new File(candidate);
            if (!fontFile.exists()) {
                continue;
            }
            BaseFont font = tryCreateEmbeddedFont(candidate);
            if (font != null) {
                return font;
            }
        }

        try {
            return BaseFont.createFont("STSong-Light", "UniGB-UCS2-H", BaseFont.NOT_EMBEDDED);
        } catch (Exception ignored) {
            try {
                return BaseFont.createFont(BaseFont.HELVETICA, BaseFont.WINANSI, BaseFont.NOT_EMBEDDED);
            } catch (Exception e) {
                throw new IOException("PDF font initialization failed", e);
            }
        }
    }

    private BaseFont tryCreateEmbeddedFont(String path) {
        try {
            return BaseFont.createFont(path, BaseFont.IDENTITY_H, BaseFont.EMBEDDED);
        } catch (Exception ignored) {
            // Some TTC collections require an explicit sub-font index.
        }
        if (path.toLowerCase().endsWith(".ttc")) {
            for (int i = 0; i < 4; i++) {
                try {
                    return BaseFont.createFont(path + "," + i, BaseFont.IDENTITY_H, BaseFont.EMBEDDED);
                } catch (Exception ignored) {
                    // Try the next sub-font index.
                }
            }
        }
        return null;
    }
}
