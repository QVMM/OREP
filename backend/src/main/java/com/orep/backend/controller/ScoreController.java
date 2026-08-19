package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.ScoreResultVO;
import com.orep.backend.dto.ScoreSubmitRequest;
import com.orep.backend.entity.ScoreItem;
import com.orep.backend.mapper.ScoreDetailMapper;
import com.orep.backend.mapper.ScoreItemMapper;
import com.orep.backend.service.PdfService;
import com.orep.backend.service.ScoreService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.List;

@RestController
@RequestMapping("/api/score")
public class ScoreController {

    @Autowired
    private ScoreService scoreService;
    @Autowired
    private PdfService pdfService;
    @Autowired
    private ScoreItemMapper scoreItemMapper;

    @GetMapping("/items")
    public Result<List<ScoreItem>> getItems(@RequestParam(required = false) Long templateId) {
        return Result.success(scoreService.getScoreItems(templateId));
    }

    @PostMapping("/submit")
    public Result<Void> submit(@RequestBody ScoreSubmitRequest request, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        Long tenantId = (Long) req.getAttribute("tenantId");
        scoreService.submitScore(request, userId, tenantId);
        return Result.success();
    }

    @GetMapping("/result")
    public Result<ScoreResultVO> getResult(@RequestParam Long meetingId, HttpServletRequest req) {
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        return Result.success(scoreService.getScoreResult(meetingId, userId, role));
    }

    @GetMapping("/export-pdf")
    public void exportPdf(@RequestParam Long meetingId, HttpServletRequest req, HttpServletResponse response) throws Exception {
        Long userId = (Long) req.getAttribute("userId");
        String role = (String) req.getAttribute("role");
        ScoreResultVO result = scoreService.getScoreResult(meetingId, userId, role);
        byte[] pdf = pdfService.generateScoreReport(result);

        response.setContentType("application/pdf");
        response.setHeader("Content-Disposition",
                "attachment; filename=" + URLEncoder.encode("评分报告_" + result.getMeetingTitle(), StandardCharsets.UTF_8) + ".pdf");
        response.setContentLength(pdf.length);
        response.getOutputStream().write(pdf);
        response.getOutputStream().flush();
    }

    @Autowired
    private ScoreDetailMapper scoreDetailMapper;

    /**
     * 重新初始化评分项（修复乱码数据）
     * 2025年世界职业院校技能大赛总决赛评分标准
     */
    @PostMapping("/reinit-items")
    public Result<Integer> reinitItems(HttpServletRequest req) {
        // 先删除评分详情（外键依赖），再删除评分项
        scoreDetailMapper.delete(null);
        scoreItemMapper.delete(null);

        // 一、技能水平（60分）
        insertItem(1L, "一、技能水平（权重60%，60分）", "操作规范性", new BigDecimal("10"), "技能操作规范，符合行业标准和岗位要求", 1);
        insertItem(1L, "一、技能水平（权重60%，60分）", "技能熟练度", new BigDecimal("15"), "知识技术应用和软硬件等工具使用熟练，操作流畅，运用精准，任务进度控制和时间利用合理", 2);
        insertItem(1L, "一、技能水平（权重60%，60分）", "任务难易度", new BigDecimal("15"), "工作任务完整，突出关键技术，具有一定挑战性，需要较高技能操作水平和解决复杂问题的综合能力", 3);
        insertItem(1L, "一、技能水平（权重60%，60分）", "技术先进性", new BigDecimal("15"), "体现所属行业新标准、新技术、新场景应用，积极应用前沿技术、数字化技术，技术选择恰当", 4);
        insertItem(1L, "一、技能水平（权重60%，60分）", "现场讲解效果", new BigDecimal("5"), "讲解内容逻辑清晰，重点突出，表达准确", 5);

        // 二、职业素养（10分）
        insertItem(1L, "二、职业素养（权重10%，10分）", "职业道德与行为规范", new BigDecimal("4"), "诚信守法，尊重知识产权，遵守职业伦理，展现良好职业风貌", 6);
        insertItem(1L, "二、职业素养（权重10%，10分）", "工匠精神", new BigDecimal("3"), "注重细节，精益求精，追求卓越，体现管理意识和质量意识", 7);
        insertItem(1L, "二、职业素养（权重10%，10分）", "安全意识", new BigDecimal("3"), "严格遵守安全规范，具备劳动保护和风险防范意识", 8);

        // 三、应用价值（10分）
        insertItem(1L, "三、应用价值（权重10%，10分）", "实用性", new BigDecimal("4"), "解决方案可直接应用于实践，有效解决生产、生活中的实际问题，契合产业转型升级、区域经济社会发展、乡村振兴、促进高质量就业等国家战略需求", 9);
        insertItem(1L, "三、应用价值（权重10%，10分）", "经济性", new BigDecimal("3"), "资源利用合理，体现高效益、高质量", 10);
        insertItem(1L, "三、应用价值（权重10%，10分）", "可持续性", new BigDecimal("3"), "具有良好环保意识，绿色低碳，符合产业未来发展方向", 11);

        // 四、团队合作（10分）
        insertItem(1L, "四、团队合作（权重10%，10分）", "团队精神", new BigDecimal("5"), "团队成员能够准确理解共同目标和任务，清楚自己的角色定位和职责，团队成员相互尊重、信任和支持，拥有良好的团队氛围", 12);
        insertItem(1L, "四、团队合作（权重10%，10分）", "沟通协作", new BigDecimal("5"), "团队成员在比赛中能够有效沟通、紧密协作，能够相互补台，共同应对突发情况", 13);

        // 五、创新创意（10分）
        insertItem(1L, "五、创新创意（权重10%，10分）", "创新意识", new BigDecimal("4"), "体现原始创意、创新和团队成员创新精神、创新能力", 14);
        insertItem(1L, "五、创新创意（权重10%，10分）", "创新成效", new BigDecimal("6"), "在要素整合、新技术应用、工艺流程改进、服务模式优化等方面具有原创性，侧重加工工艺创新、实用技术创新、产品（技术）数字化改良、应用性优化、民生类创意等", 15);

        return Result.success(15);
    }

    private void insertItem(Long templateId, String category, String name, BigDecimal maxScore, String description, int sortOrder) {
        ScoreItem item = new ScoreItem();
        item.setTemplateId(templateId);
        item.setCategory(category);
        item.setName(name);
        item.setMaxScore(maxScore);
        item.setDescription(description);
        item.setSortOrder(sortOrder);
        scoreItemMapper.insert(item);
    }
}
