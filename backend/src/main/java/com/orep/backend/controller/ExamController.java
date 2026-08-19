package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.ExamAttemptVO;
import com.orep.backend.dto.ExamQuestionVO;
import com.orep.backend.dto.ExamSubmitResultVO;
import com.orep.backend.entity.ExamPaper;
import com.orep.backend.service.ExamService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/exams")
public class ExamController {
    private final ExamService examService;

    public ExamController(ExamService examService) {
        this.examService = examService;
    }

    @GetMapping
    public Result<List<ExamPaper>> listPapers() {
        return Result.success(examService.listPapers(false));
    }

    @PostMapping("/{paperId}/start")
    public Result<ExamAttemptVO> start(@PathVariable Long paperId, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        ExamAttemptVO attempt = examService.startAttempt(userId, paperId);
        if (attempt == null) return Result.error(404, "考试不存在或未发布");
        return Result.success(attempt);
    }

    @PostMapping("/attempts/{attemptId}/submit")
    public Result<ExamSubmitResultVO> submit(
            @PathVariable Long attemptId,
            @RequestBody Map<String, String> body,
            HttpServletRequest request
    ) {
        Long userId = (Long) request.getAttribute("userId");
        Map<Long, String> answers = body.entrySet().stream()
                .collect(Collectors.toMap(entry -> Long.parseLong(entry.getKey()), Map.Entry::getValue));
        ExamSubmitResultVO result = examService.submitAttempt(userId, attemptId, answers);
        if (result == null) return Result.error(404, "考试记录不存在");
        return Result.success(result);
    }

    @PostMapping("/attempts/{attemptId}/screen-leave")
    public Result<Void> reportScreenLeave(@PathVariable Long attemptId, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        examService.reportScreenLeave(userId, attemptId);
        return Result.success();
    }

    @GetMapping("/wrong-questions")
    public Result<List<ExamQuestionVO>> wrongQuestions(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        return Result.success(examService.listWrongQuestions(userId));
    }

    @GetMapping("/favorites")
    public Result<List<ExamQuestionVO>> favorites(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        return Result.success(examService.listFavoriteQuestions(userId));
    }

    @PostMapping("/questions/{questionId}/favorite")
    public Result<Void> toggleFavorite(@PathVariable Long questionId, HttpServletRequest request) {
        Long userId = (Long) request.getAttribute("userId");
        examService.toggleFavorite(userId, questionId);
        return Result.success();
    }
}
