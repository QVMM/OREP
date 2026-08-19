package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.BatchDeleteRequest;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.dto.ExamManualGradeRequest;
import com.orep.backend.dto.ExamPaperDetailVO;
import com.orep.backend.dto.ExamPaperRequest;
import com.orep.backend.dto.ExamQuestionRequest;
import com.orep.backend.dto.ExamReviewVO;
import com.orep.backend.entity.ExamPaper;
import com.orep.backend.entity.ExamQuestion;
import com.orep.backend.service.ExamService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/admin/exams")
public class AdminExamController {
    private final ExamService examService;

    public AdminExamController(ExamService examService) {
        this.examService = examService;
    }

    @GetMapping("/questions")
    public Result<List<ExamQuestion>> listQuestions(HttpServletRequest request) {
        return Result.success(examService.listQuestions(userId(request), role(request)));
    }

    @PostMapping("/questions")
    public Result<ExamQuestion> createQuestion(@RequestBody ExamQuestionRequest body, HttpServletRequest request) {
        return Result.success(examService.createQuestion(body, userId(request)));
    }

    @PutMapping("/questions/{id}")
    public Result<ExamQuestion> updateQuestion(@PathVariable Long id, @RequestBody ExamQuestionRequest body, HttpServletRequest request) {
        ExamQuestion question = examService.updateQuestion(id, body, userId(request), role(request));
        if (question == null) return Result.error(404, "题目不存在");
        return Result.success(question);
    }

    @DeleteMapping("/questions/{id}")
    public Result<Void> deleteQuestion(@PathVariable Long id, HttpServletRequest request) {
        if (!examService.deleteQuestion(id, userId(request), role(request))) return Result.error(404, "题目不存在");
        return Result.success();
    }

    @PostMapping("/questions/batch-delete")
    public Result<BatchDeleteResult> batchDeleteQuestions(@RequestBody BatchDeleteRequest body, HttpServletRequest request) {
        return Result.success(examService.deleteQuestions(body.getIds(), userId(request), role(request)));
    }

    @GetMapping("/papers")
    public Result<List<ExamPaper>> listPapers(HttpServletRequest request) {
        return Result.success(examService.listAdminPapers(userId(request), role(request)));
    }

    @GetMapping("/papers/{id}")
    public Result<ExamPaperDetailVO> getPaper(@PathVariable Long id, HttpServletRequest request) {
        ExamPaperDetailVO paper = examService.getPaperDetail(id, userId(request), role(request));
        if (paper == null) return Result.error(404, "考试不存在");
        return Result.success(paper);
    }

    @PostMapping("/papers")
    public Result<ExamPaper> createPaper(@RequestBody ExamPaperRequest body, HttpServletRequest request) {
        return Result.success(examService.createPaper(body, userId(request), role(request)));
    }

    @PutMapping("/papers/{id}")
    public Result<ExamPaper> updatePaper(@PathVariable Long id, @RequestBody ExamPaperRequest body, HttpServletRequest request) {
        ExamPaper paper = examService.updatePaper(id, body, userId(request), role(request));
        if (paper == null) return Result.error(404, "考试不存在");
        return Result.success(paper);
    }

    @DeleteMapping("/papers/{id}")
    public Result<Void> deletePaper(@PathVariable Long id, HttpServletRequest request) {
        if (!examService.deletePaper(id, userId(request), role(request))) return Result.error(404, "考试不存在");
        return Result.success();
    }

    @PostMapping("/papers/batch-delete")
    public Result<BatchDeleteResult> batchDeletePapers(@RequestBody BatchDeleteRequest body, HttpServletRequest request) {
        return Result.success(examService.deletePapers(body.getIds(), userId(request), role(request)));
    }

    @GetMapping("/reviews/pending")
    public Result<List<ExamReviewVO>> listPendingReviews(HttpServletRequest request) {
        return Result.success(examService.listPendingReviews(userId(request), role(request)));
    }

    @GetMapping("/reviews/{attemptId}")
    public Result<ExamReviewVO> getReview(@PathVariable Long attemptId, HttpServletRequest request) {
        ExamReviewVO review = examService.getReviewDetail(attemptId, userId(request), role(request));
        if (review == null) return Result.error(404, "考试记录不存在");
        return Result.success(review);
    }

    @PostMapping("/reviews/{attemptId}/grade")
    public Result<ExamReviewVO> gradeReview(@PathVariable Long attemptId, @RequestBody ExamManualGradeRequest body, HttpServletRequest request) {
        ExamReviewVO review = examService.gradeManualAnswers(attemptId, body, userId(request), role(request));
        if (review == null) return Result.error(404, "考试记录不存在");
        return Result.success(review);
    }

    private Long userId(HttpServletRequest request) {
        return (Long) request.getAttribute("userId");
    }

    private String role(HttpServletRequest request) {
        return String.valueOf(request.getAttribute("role"));
    }
}
