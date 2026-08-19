package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.ExamAttemptVO;
import com.orep.backend.dto.BatchDeleteResult;
import com.orep.backend.dto.ExamManualGradeRequest;
import com.orep.backend.dto.ExamPaperDetailVO;
import com.orep.backend.dto.ExamPaperRequest;
import com.orep.backend.dto.ExamQuestionRequest;
import com.orep.backend.dto.ExamQuestionVO;
import com.orep.backend.dto.ExamReviewVO;
import com.orep.backend.dto.ExamSubmitResultVO;
import com.orep.backend.entity.ExamAttempt;
import com.orep.backend.entity.ExamAttemptAnswer;
import com.orep.backend.entity.ExamFavorite;
import com.orep.backend.entity.ExamPaper;
import com.orep.backend.entity.ExamPaperQuestion;
import com.orep.backend.entity.ExamQuestion;
import com.orep.backend.entity.ExamWrongQuestion;
import com.orep.backend.mapper.ExamAttemptAnswerMapper;
import com.orep.backend.mapper.ExamAttemptMapper;
import com.orep.backend.mapper.ExamFavoriteMapper;
import com.orep.backend.mapper.ExamPaperMapper;
import com.orep.backend.mapper.ExamPaperQuestionMapper;
import com.orep.backend.mapper.ExamQuestionMapper;
import com.orep.backend.mapper.ExamWrongQuestionMapper;
import com.orep.backend.security.AdminAccess;
import jakarta.annotation.PostConstruct;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class ExamService {
    private final ExamQuestionMapper questionMapper;
    private final ExamPaperMapper paperMapper;
    private final ExamPaperQuestionMapper paperQuestionMapper;
    private final ExamAttemptMapper attemptMapper;
    private final ExamAttemptAnswerMapper answerMapper;
    private final ExamWrongQuestionMapper wrongMapper;
    private final ExamFavoriteMapper favoriteMapper;
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ExamService(
            ExamQuestionMapper questionMapper,
            ExamPaperMapper paperMapper,
            ExamPaperQuestionMapper paperQuestionMapper,
            ExamAttemptMapper attemptMapper,
            ExamAttemptAnswerMapper answerMapper,
            ExamWrongQuestionMapper wrongMapper,
            ExamFavoriteMapper favoriteMapper,
            JdbcTemplate jdbc
    ) {
        this.questionMapper = questionMapper;
        this.paperMapper = paperMapper;
        this.paperQuestionMapper = paperQuestionMapper;
        this.attemptMapper = attemptMapper;
        this.answerMapper = answerMapper;
        this.wrongMapper = wrongMapper;
        this.favoriteMapper = favoriteMapper;
        this.jdbc = jdbc;
    }

    @PostConstruct
    public void ensureSchema() {
        addColumn("exam_question", "created_by", "BIGINT DEFAULT NULL COMMENT '创建者用户ID' AFTER status");
        addColumn("exam_paper", "created_by", "BIGINT DEFAULT NULL COMMENT '创建者用户ID' AFTER anti_cheat_enabled");
        addIndex("exam_question", "idx_exam_question_created_by", "ALTER TABLE exam_question ADD KEY idx_exam_question_created_by (created_by)");
        addIndex("exam_paper", "idx_exam_paper_created_by", "ALTER TABLE exam_paper ADD KEY idx_exam_paper_created_by (created_by)");
    }

    private void addColumn(String table, String column, String ddl) {
        if (jdbc == null) return;
        try {
            jdbc.execute("ALTER TABLE " + table + " ADD COLUMN " + column + " " + ddl);
        } catch (Exception ignored) {
        }
    }

    private void addIndex(String table, String index, String ddl) {
        if (jdbc == null) return;
        try {
            jdbc.execute(ddl);
        } catch (Exception ignored) {
        }
    }

    public List<ExamQuestion> listQuestions(Long userId, String role) {
        return questionMapper.selectList(
                new LambdaQueryWrapper<ExamQuestion>()
                        .eq(isTeacher(role), ExamQuestion::getCreatedBy, userId)
                        .orderByDesc(ExamQuestion::getCreatedAt)
        );
    }

    public ExamQuestion createQuestion(ExamQuestionRequest request, Long creatorId) {
        ExamQuestion question = new ExamQuestion();
        applyQuestion(question, request);
        question.setCreatedBy(creatorId);
        if (question.getStatus() == null || question.getStatus().isBlank()) question.setStatus("enabled");
        questionMapper.insert(question);
        return question;
    }

    public ExamQuestion updateQuestion(Long id, ExamQuestionRequest request, Long userId, String role) {
        ExamQuestion question = questionMapper.selectById(id);
        if (!canAccessQuestion(question, userId, role)) return null;
        applyQuestion(question, request);
        questionMapper.updateById(question);
        return question;
    }

    public boolean deleteQuestion(Long id, Long userId, String role) {
        ExamQuestion question = questionMapper.selectById(id);
        if (!canAccessQuestion(question, userId, role)) return false;
        return questionMapper.deleteById(id) > 0;
    }

    @Transactional
    public BatchDeleteResult deleteQuestions(List<Long> ids, Long userId, String role) {
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> normalizedIds = normalizeIds(ids);
        result.setRequested(normalizedIds.size());
        for (Long id : normalizedIds) {
            if (deleteQuestion(id, userId, role)) {
                result.addDeleted();
            } else {
                result.addFailure(id, "题目不存在或无权删除");
            }
        }
        return result;
    }

    public List<ExamPaper> listPapers(boolean admin) {
        LambdaQueryWrapper<ExamPaper> wrapper = new LambdaQueryWrapper<ExamPaper>().orderByDesc(ExamPaper::getCreatedAt);
        if (!admin) wrapper.eq(ExamPaper::getStatus, "published");
        return paperMapper.selectList(wrapper);
    }

    public List<ExamPaper> listAdminPapers(Long userId, String role) {
        return paperMapper.selectList(
                new LambdaQueryWrapper<ExamPaper>()
                        .eq(isTeacher(role), ExamPaper::getCreatedBy, userId)
                        .orderByDesc(ExamPaper::getCreatedAt)
        );
    }

    public ExamPaper createPaper(ExamPaperRequest request, Long creatorId, String role) {
        if (!canUsePaperQuestions(request, creatorId, role)) {
            throw new RuntimeException("试卷包含无权使用的题目");
        }
        ExamPaper paper = new ExamPaper();
        applyPaper(paper, request);
        paper.setCreatedBy(creatorId);
        paperMapper.insert(paper);
        savePaperQuestions(paper.getId(), request.getQuestions());
        return paper;
    }

    public ExamPaperDetailVO getPaperDetail(Long id, Long userId, String role) {
        ExamPaper paper = paperMapper.selectById(id);
        if (!canAccessPaper(paper, userId, role)) return null;
        ExamPaperDetailVO detail = new ExamPaperDetailVO();
        detail.setId(paper.getId());
        detail.setTitle(paper.getTitle());
        detail.setDescription(paper.getDescription());
        detail.setDurationMinutes(paper.getDurationMinutes());
        detail.setPassScore(paper.getPassScore());
        detail.setStatus(paper.getStatus());
        detail.setShuffleQuestions(paper.getShuffleQuestions());
        detail.setShuffleOptions(paper.getShuffleOptions());
        detail.setAntiCheatEnabled(paper.getAntiCheatEnabled());
        detail.setCreatedAt(paper.getCreatedAt());
        detail.setUpdatedAt(paper.getUpdatedAt());
        detail.setQuestions(loadPaperQuestionConfigs(id));
        return detail;
    }

    public ExamPaper updatePaper(Long id, ExamPaperRequest request, Long userId, String role) {
        ExamPaper paper = paperMapper.selectById(id);
        if (!canAccessPaper(paper, userId, role)) return null;
        if (!canUsePaperQuestions(request, userId, role)) {
            throw new RuntimeException("试卷包含无权使用的题目");
        }
        applyPaper(paper, request);
        paperMapper.updateById(paper);
        paperQuestionMapper.delete(new LambdaQueryWrapper<ExamPaperQuestion>().eq(ExamPaperQuestion::getPaperId, id));
        savePaperQuestions(id, request.getQuestions());
        return paper;
    }

    public boolean deletePaper(Long id, Long userId, String role) {
        ExamPaper paper = paperMapper.selectById(id);
        if (!canAccessPaper(paper, userId, role)) return false;
        paperQuestionMapper.delete(new LambdaQueryWrapper<ExamPaperQuestion>().eq(ExamPaperQuestion::getPaperId, id));
        return paperMapper.deleteById(id) > 0;
    }

    @Transactional
    public BatchDeleteResult deletePapers(List<Long> ids, Long userId, String role) {
        BatchDeleteResult result = new BatchDeleteResult();
        List<Long> normalizedIds = normalizeIds(ids);
        result.setRequested(normalizedIds.size());
        for (Long id : normalizedIds) {
            if (deletePaper(id, userId, role)) {
                result.addDeleted();
            } else {
                result.addFailure(id, "考试不存在或无权删除");
            }
        }
        return result;
    }

    public ExamAttemptVO startAttempt(Long userId, Long paperId) {
        ExamPaper paper = paperMapper.selectById(paperId);
        if (paper == null || !"published".equals(paper.getStatus())) return null;
        List<ExamQuestion> questions = loadPaperQuestions(paperId);
        ExamAttempt attempt = new ExamAttempt();
        attempt.setPaperId(paperId);
        attempt.setUserId(userId);
        attempt.setStatus("in_progress");
        attempt.setStartedAt(LocalDateTime.now());
        attempt.setDeadlineAt(LocalDateTime.now().plusMinutes(Math.max(1, paper.getDurationMinutes() == null ? 45 : paper.getDurationMinutes())));
        attempt.setScreenLeaveCount(0);
        attempt.setQuestionCount(questions.size());
        attempt.setTotalScore(questions.stream().mapToInt(q -> q.getScore() == null ? 0 : q.getScore()).sum());
        attemptMapper.insert(attempt);

        if (Boolean.TRUE.equals(paper.getShuffleQuestions())) {
            questions = new ArrayList<>(questions);
            java.util.Collections.shuffle(questions, new Random(attempt.getId() == null ? System.nanoTime() : attempt.getId()));
        }

        ExamAttemptVO vo = new ExamAttemptVO();
        vo.setAttemptId(attempt.getId());
        vo.setPaperId(paper.getId());
        vo.setTitle(paper.getTitle());
        vo.setDurationMinutes(paper.getDurationMinutes());
        vo.setDeadlineAt(attempt.getDeadlineAt());
        vo.setAntiCheatEnabled(Boolean.TRUE.equals(paper.getAntiCheatEnabled()));
        vo.setScreenLeaveCount(0);
        vo.setQuestions(questions.stream().map(question -> {
            ExamQuestionVO item = toStudentQuestion(question);
            if (Boolean.TRUE.equals(paper.getShuffleOptions()) && isChoice(question.getQuestionType())) {
                item.setOptionsJson(shuffleOptions(question.getOptionsJson(), attempt.getId()));
            }
            return item;
        }).toList());
        return vo;
    }

    public ExamSubmitResultVO submitAttempt(Long userId, Long attemptId, Map<Long, String> answers) {
        ExamAttempt attempt = attemptMapper.selectById(attemptId);
        if (attempt == null || !Objects.equals(attempt.getUserId(), userId)) return null;
        if ("submitted".equals(attempt.getStatus())) throw new IllegalStateException("考试已提交");
        if (attempt.getDeadlineAt() != null && LocalDateTime.now().isAfter(attempt.getDeadlineAt().plusSeconds(30))) {
            attempt.setStatus("timeout_submitted");
        } else {
            attempt.setStatus("submitted");
        }

        ExamPaper paper = paperMapper == null ? null : paperMapper.selectById(attempt.getPaperId());
        List<ExamQuestion> questions = loadPaperQuestions(attempt.getPaperId());
        int score = 0;
        int correctCount = 0;
        int manualQuestionCount = 0;
        List<ExamSubmitResultVO.WrongQuestion> wrongQuestions = new ArrayList<>();
        for (ExamQuestion question : questions) {
            String answer = answers == null ? null : answers.get(question.getId());
            if ("programming".equals(question.getQuestionType())) {
                manualQuestionCount++;
                saveAttemptAnswer(attemptId, question.getId(), answer, null, 0);
                continue;
            }
            boolean correct = scoreQuestion(question, answer);
            int questionScore = correct ? (question.getScore() == null ? 0 : question.getScore()) : 0;
            score += questionScore;
            if (correct) correctCount++;
            saveAttemptAnswer(attemptId, question.getId(), answer, correct, questionScore);
            if (!correct) {
                wrongQuestions.add(toWrongQuestion(question));
                recordWrongQuestion(userId, attemptId, question.getId());
            }
        }
        int totalScore = questions.stream().mapToInt(q -> q.getScore() == null ? 0 : q.getScore()).sum();
        boolean manualReviewRequired = manualQuestionCount > 0;
        if (manualReviewRequired) {
            attempt.setStatus("pending_review");
        }
        attempt.setScore(score);
        attempt.setTotalScore(totalScore);
        attempt.setCorrectCount(correctCount);
        attempt.setQuestionCount(questions.size());
        attempt.setSubmittedAt(LocalDateTime.now());
        attemptMapper.updateById(attempt);

        ExamSubmitResultVO result = new ExamSubmitResultVO();
        result.setAttemptId(attemptId);
        result.setScore(score);
        result.setTotalScore(totalScore);
        result.setCorrectCount(correctCount);
        result.setQuestionCount(questions.size());
        int passScore = paper == null || paper.getPassScore() == null ? 60 : paper.getPassScore();
        result.setPassed(!manualReviewRequired && score >= passScore);
        result.setManualReviewRequired(manualReviewRequired);
        result.setManualQuestionCount(manualQuestionCount);
        result.setWrongQuestions(wrongQuestions);
        return result;
    }

    public List<ExamReviewVO> listPendingReviews(Long userId, String role) {
        LambdaQueryWrapper<ExamAttempt> wrapper = new LambdaQueryWrapper<ExamAttempt>()
                .eq(ExamAttempt::getStatus, "pending_review")
                .orderByDesc(ExamAttempt::getSubmittedAt);
        if (isTeacher(role)) {
            List<Long> paperIds = listAdminPapers(userId, role).stream().map(ExamPaper::getId).toList();
            if (paperIds.isEmpty()) return List.of();
            wrapper.in(ExamAttempt::getPaperId, paperIds);
        }
        List<ExamAttempt> attempts = attemptMapper.selectList(wrapper);
        if (attempts == null || attempts.isEmpty()) return List.of();
        Map<Long, ExamPaper> paperById = paperMapper.selectBatchIds(
                attempts.stream().map(ExamAttempt::getPaperId).filter(Objects::nonNull).collect(Collectors.toSet())
        ).stream().collect(Collectors.toMap(ExamPaper::getId, item -> item));
        return attempts.stream().map(attempt -> {
            ExamReviewVO vo = new ExamReviewVO();
            ExamPaper paper = paperById.get(attempt.getPaperId());
            vo.setAttemptId(attempt.getId());
            vo.setPaperId(attempt.getPaperId());
            vo.setPaperTitle(paper == null ? "未知考试" : paper.getTitle());
            vo.setUserId(attempt.getUserId());
            vo.setStatus(attempt.getStatus());
            vo.setScore(attempt.getScore());
            vo.setTotalScore(attempt.getTotalScore());
            vo.setSubmittedAt(attempt.getSubmittedAt());
            return vo;
        }).toList();
    }

    public ExamReviewVO getReviewDetail(Long attemptId, Long userId, String role) {
        ExamAttempt attempt = attemptMapper.selectById(attemptId);
        if (attempt == null) return null;
        ExamPaper paper = paperMapper.selectById(attempt.getPaperId());
        if (!canAccessPaper(paper, userId, role)) return null;
        List<ExamQuestion> paperQuestions = loadPaperQuestions(attempt.getPaperId());
        Map<Long, ExamQuestion> questionById = paperQuestions.stream().collect(Collectors.toMap(ExamQuestion::getId, item -> item));
        List<ExamAttemptAnswer> answers = answerMapper.selectList(
                new LambdaQueryWrapper<ExamAttemptAnswer>().eq(ExamAttemptAnswer::getAttemptId, attemptId)
        );

        ExamReviewVO vo = new ExamReviewVO();
        vo.setAttemptId(attempt.getId());
        vo.setPaperId(attempt.getPaperId());
        vo.setPaperTitle(paper == null ? "未知考试" : paper.getTitle());
        vo.setUserId(attempt.getUserId());
        vo.setStatus(attempt.getStatus());
        vo.setScore(attempt.getScore());
        vo.setTotalScore(attempt.getTotalScore());
        vo.setSubmittedAt(attempt.getSubmittedAt());
        vo.setAnswers(answers.stream()
                .map(answer -> toReviewAnswer(answer, questionById.get(answer.getQuestionId())))
                .filter(Objects::nonNull)
                .toList());
        return vo;
    }

    public ExamReviewVO gradeManualAnswers(Long attemptId, ExamManualGradeRequest request, Long userId, String role) {
        ExamAttempt attempt = attemptMapper.selectById(attemptId);
        if (attempt == null) return null;
        if (!canAccessPaper(paperMapper.selectById(attempt.getPaperId()), userId, role)) return null;
        Map<Long, ExamAttemptAnswer> existing = answerMapper.selectList(
                new LambdaQueryWrapper<ExamAttemptAnswer>().eq(ExamAttemptAnswer::getAttemptId, attemptId)
        ).stream().collect(Collectors.toMap(ExamAttemptAnswer::getId, item -> item));
        List<ExamQuestion> paperQuestions = loadPaperQuestions(attempt.getPaperId());
        Map<Long, ExamQuestion> questionById = paperQuestions.stream().collect(Collectors.toMap(ExamQuestion::getId, item -> item));

        if (request != null && request.getAnswers() != null) {
            for (ExamManualGradeRequest.Item item : request.getAnswers()) {
                ExamAttemptAnswer answer = existing.get(item.getAnswerId());
                if (answer == null) continue;
                ExamQuestion question = questionById.get(answer.getQuestionId());
                if (question == null || !"programming".equals(question.getQuestionType())) continue;
                int maxScore = question.getScore() == null ? 0 : question.getScore();
                int score = Math.max(0, Math.min(maxScore, item.getScore() == null ? 0 : item.getScore()));
                answer.setScore(score);
                answer.setCorrect(score >= maxScore && maxScore > 0);
                answerMapper.updateById(answer);
            }
        }

        List<ExamAttemptAnswer> updatedAnswers = answerMapper.selectList(
                new LambdaQueryWrapper<ExamAttemptAnswer>().eq(ExamAttemptAnswer::getAttemptId, attemptId)
        );
        int totalScore = paperQuestions.stream().mapToInt(q -> q.getScore() == null ? 0 : q.getScore()).sum();
        int score = updatedAnswers.stream().mapToInt(answer -> answer.getScore() == null ? 0 : answer.getScore()).sum();
        int correctCount = (int) updatedAnswers.stream().filter(answer -> Boolean.TRUE.equals(answer.getCorrect())).count();
        attempt.setScore(score);
        attempt.setTotalScore(totalScore);
        attempt.setCorrectCount(correctCount);
        attempt.setQuestionCount(paperQuestions.size());
        attempt.setStatus("submitted");
        attemptMapper.updateById(attempt);
        return getReviewDetail(attemptId, userId, role);
    }

    public void reportScreenLeave(Long userId, Long attemptId) {
        ExamAttempt attempt = attemptMapper.selectById(attemptId);
        if (attempt == null || !Objects.equals(attempt.getUserId(), userId)) return;
        attempt.setScreenLeaveCount((attempt.getScreenLeaveCount() == null ? 0 : attempt.getScreenLeaveCount()) + 1);
        attemptMapper.updateById(attempt);
    }

    public List<ExamQuestionVO> listWrongQuestions(Long userId) {
        List<ExamWrongQuestion> wrongs = wrongMapper.selectList(
                new LambdaQueryWrapper<ExamWrongQuestion>().eq(ExamWrongQuestion::getUserId, userId).orderByDesc(ExamWrongQuestion::getLastWrongAt)
        );
        if (wrongs.isEmpty()) return List.of();
        List<Long> ids = wrongs.stream().map(ExamWrongQuestion::getQuestionId).toList();
        return questionMapper.selectBatchIds(ids).stream().map(this::toReviewQuestion).toList();
    }

    public List<ExamQuestionVO> listFavoriteQuestions(Long userId) {
        List<ExamFavorite> favorites = favoriteMapper.selectList(
                new LambdaQueryWrapper<ExamFavorite>().eq(ExamFavorite::getUserId, userId).orderByDesc(ExamFavorite::getCreatedAt)
        );
        if (favorites.isEmpty()) return List.of();
        List<Long> ids = favorites.stream().map(ExamFavorite::getQuestionId).toList();
        return questionMapper.selectBatchIds(ids).stream().map(this::toReviewQuestion).toList();
    }

    public void toggleFavorite(Long userId, Long questionId) {
        ExamFavorite existing = favoriteMapper.selectOne(
                new LambdaQueryWrapper<ExamFavorite>().eq(ExamFavorite::getUserId, userId).eq(ExamFavorite::getQuestionId, questionId)
        );
        if (existing != null) {
            favoriteMapper.deleteById(existing.getId());
            return;
        }
        ExamFavorite favorite = new ExamFavorite();
        favorite.setUserId(userId);
        favorite.setQuestionId(questionId);
        favoriteMapper.insert(favorite);
    }

    public ExamQuestionVO toStudentQuestion(ExamQuestion question) {
        ExamQuestionVO vo = baseQuestionVO(question);
        vo.setAnswerJson(null);
        vo.setAnalysis(null);
        return vo;
    }

    private ExamQuestionVO toReviewQuestion(ExamQuestion question) {
        return baseQuestionVO(question);
    }

    private ExamQuestionVO baseQuestionVO(ExamQuestion question) {
        ExamQuestionVO vo = new ExamQuestionVO();
        vo.setId(question.getId());
        vo.setQuestionType(question.getQuestionType());
        vo.setStem(question.getStem());
        vo.setOptionsJson(question.getOptionsJson());
        vo.setAnswerJson(question.getAnswerJson());
        vo.setAnalysis(question.getAnalysis());
        vo.setCategory(question.getCategory());
        vo.setDifficulty(question.getDifficulty());
        vo.setScore(question.getScore());
        vo.setStatus(question.getStatus());
        return vo;
    }

    private void applyQuestion(ExamQuestion question, ExamQuestionRequest request) {
        question.setQuestionType(nonBlank(request.getQuestionType(), "single"));
        question.setStem(nonBlank(request.getStem(), "新题目"));
        question.setOptionsJson(nonBlank(request.getOptionsJson(), "[]"));
        question.setAnswerJson(nonBlank(request.getAnswerJson(), "[]"));
        question.setAnalysis(request.getAnalysis());
        question.setCategory(nonBlank(request.getCategory(), "通用"));
        question.setDifficulty(nonBlank(request.getDifficulty(), "normal"));
        question.setScore(request.getScore() == null ? 5 : request.getScore());
        question.setStatus(nonBlank(request.getStatus(), "enabled"));
    }

    private void applyPaper(ExamPaper paper, ExamPaperRequest request) {
        paper.setTitle(nonBlank(request.getTitle(), "新考试"));
        paper.setDescription(request.getDescription());
        paper.setDurationMinutes(request.getDurationMinutes() == null ? 45 : request.getDurationMinutes());
        paper.setPassScore(request.getPassScore() == null ? 60 : request.getPassScore());
        paper.setStatus(nonBlank(request.getStatus(), "draft"));
        paper.setShuffleQuestions(request.getShuffleQuestions() == null || request.getShuffleQuestions());
        paper.setShuffleOptions(request.getShuffleOptions() == null || request.getShuffleOptions());
        paper.setAntiCheatEnabled(request.getAntiCheatEnabled() == null || request.getAntiCheatEnabled());
    }

    private void savePaperQuestions(Long paperId, List<ExamPaperRequest.QuestionConfig> questions) {
        if (questions == null) return;
        for (ExamPaperRequest.QuestionConfig item : questions) {
            if (item.getQuestionId() == null) continue;
            ExamPaperQuestion link = new ExamPaperQuestion();
            link.setPaperId(paperId);
            link.setQuestionId(item.getQuestionId());
            link.setScore(item.getScore() == null ? 5 : item.getScore());
            link.setSortOrder(item.getSortOrder() == null ? 0 : item.getSortOrder());
            paperQuestionMapper.insert(link);
        }
    }

    private boolean canUsePaperQuestions(ExamPaperRequest request, Long userId, String role) {
        if (!isTeacher(role) || request == null || request.getQuestions() == null) return true;
        List<Long> ids = request.getQuestions().stream()
                .map(ExamPaperRequest.QuestionConfig::getQuestionId)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        if (ids.isEmpty()) return true;
        List<ExamQuestion> questions = questionMapper.selectBatchIds(ids);
        if (questions.size() != ids.size()) return false;
        return questions.stream().allMatch(question -> canAccessQuestion(question, userId, role));
    }

    private boolean canAccessQuestion(ExamQuestion question, Long userId, String role) {
        if (question == null) return false;
        if (!isTeacher(role)) return true;
        return userId != null && Objects.equals(question.getCreatedBy(), userId);
    }

    private boolean canAccessPaper(ExamPaper paper, Long userId, String role) {
        if (paper == null) return false;
        if (!isTeacher(role)) return true;
        return userId != null && Objects.equals(paper.getCreatedBy(), userId);
    }

    private boolean isTeacher(String role) {
        return "TEACHER".equals(AdminAccess.normalizeRole(role));
    }

    private List<ExamPaperRequest.QuestionConfig> loadPaperQuestionConfigs(Long paperId) {
        if (paperQuestionMapper == null || paperId == null) return List.of();
        List<ExamPaperQuestion> links = paperQuestionMapper.selectList(
                new LambdaQueryWrapper<ExamPaperQuestion>().eq(ExamPaperQuestion::getPaperId, paperId).orderByAsc(ExamPaperQuestion::getSortOrder)
        );
        if (links == null || links.isEmpty()) return List.of();
        return links.stream().map(link -> {
            ExamPaperRequest.QuestionConfig item = new ExamPaperRequest.QuestionConfig();
            item.setQuestionId(link.getQuestionId());
            item.setScore(link.getScore());
            item.setSortOrder(link.getSortOrder());
            return item;
        }).toList();
    }

    private List<ExamQuestion> loadPaperQuestions(Long paperId) {
        if (paperQuestionMapper == null || questionMapper == null || paperId == null) return List.of();
        List<ExamPaperQuestion> links = paperQuestionMapper.selectList(
                new LambdaQueryWrapper<ExamPaperQuestion>().eq(ExamPaperQuestion::getPaperId, paperId).orderByAsc(ExamPaperQuestion::getSortOrder)
        );
        if (links == null || links.isEmpty()) return List.of();
        Map<Long, ExamPaperQuestion> linkByQuestion = links.stream().collect(Collectors.toMap(ExamPaperQuestion::getQuestionId, item -> item, (a, b) -> a));
        return questionMapper.selectBatchIds(linkByQuestion.keySet()).stream()
                .peek(question -> question.setScore(linkByQuestion.get(question.getId()).getScore()))
                .sorted(Comparator.comparing(question -> linkByQuestion.get(question.getId()).getSortOrder(), Comparator.nullsLast(Integer::compareTo)))
                .toList();
    }

    private boolean scoreQuestion(ExamQuestion question, String answerJson) {
        if ("programming".equals(question.getQuestionType())) {
            return normalizeText(question.getAnswerJson()).equals(normalizeText(answerJson));
        }
        if ("blank".equals(question.getQuestionType()) || "judge".equals(question.getQuestionType()) || "single".equals(question.getQuestionType())) {
            return normalizeText(question.getAnswerJson()).equals(normalizeText(answerJson));
        }
        if ("multiple".equals(question.getQuestionType())) {
            return new HashSet<>(readStringList(question.getAnswerJson())).equals(new HashSet<>(readStringList(answerJson)));
        }
        return false;
    }

    private ExamReviewVO.AnswerItem toReviewAnswer(ExamAttemptAnswer answer, ExamQuestion question) {
        if (question == null || !"programming".equals(question.getQuestionType())) return null;
        ExamReviewVO.AnswerItem item = new ExamReviewVO.AnswerItem();
        item.setAnswerId(answer.getId());
        item.setQuestionId(question.getId());
        item.setStem(question.getStem());
        item.setReferenceAnswerJson(question.getAnswerJson());
        item.setStudentAnswerJson(answer.getAnswerJson());
        item.setScore(answer.getScore());
        item.setMaxScore(question.getScore());
        item.setCorrect(answer.getCorrect());
        return item;
    }

    private void saveAttemptAnswer(Long attemptId, Long questionId, String answerJson, Boolean correct, int score) {
        ExamAttemptAnswer answer = new ExamAttemptAnswer();
        answer.setAttemptId(attemptId);
        answer.setQuestionId(questionId);
        answer.setAnswerJson(answerJson == null ? "[]" : answerJson);
        answer.setCorrect(correct);
        answer.setScore(score);
        answerMapper.insert(answer);
    }

    private void recordWrongQuestion(Long userId, Long attemptId, Long questionId) {
        ExamWrongQuestion existing = wrongMapper.selectOne(
                new LambdaQueryWrapper<ExamWrongQuestion>().eq(ExamWrongQuestion::getUserId, userId).eq(ExamWrongQuestion::getQuestionId, questionId)
        );
        if (existing == null) {
            existing = new ExamWrongQuestion();
            existing.setUserId(userId);
            existing.setQuestionId(questionId);
            existing.setWrongCount(0);
        }
        existing.setLastAttemptId(attemptId);
        existing.setWrongCount((existing.getWrongCount() == null ? 0 : existing.getWrongCount()) + 1);
        existing.setLastWrongAt(LocalDateTime.now());
        if (existing.getId() == null) wrongMapper.insert(existing);
        else wrongMapper.updateById(existing);
    }

    private ExamSubmitResultVO.WrongQuestion toWrongQuestion(ExamQuestion question) {
        ExamSubmitResultVO.WrongQuestion wrong = new ExamSubmitResultVO.WrongQuestion();
        wrong.setQuestionId(question.getId());
        wrong.setStem(question.getStem());
        wrong.setAnalysis(question.getAnalysis());
        wrong.setAnswerJson(question.getAnswerJson());
        return wrong;
    }

    private String shuffleOptions(String optionsJson, Long seed) {
        try {
            List<Map<String, Object>> options = objectMapper.readValue(optionsJson, new TypeReference<>() {});
            java.util.Collections.shuffle(options, new Random(seed == null ? System.nanoTime() : seed));
            return objectMapper.writeValueAsString(options);
        } catch (Exception e) {
            return optionsJson;
        }
    }

    private List<String> readStringList(String json) {
        try {
            if (json == null || json.isBlank()) return List.of();
            return objectMapper.readValue(json, new TypeReference<List<String>>() {});
        } catch (Exception e) {
            return List.of(plainText(json));
        }
    }

    private String normalizeText(String text) {
        if (text == null) return "";
        return String.join("|", readStringList(text)).trim().toLowerCase();
    }

    private String plainText(String text) {
        return text == null ? "" : text.trim().toLowerCase();
    }

    private boolean isChoice(String type) {
        return "single".equals(type) || "multiple".equals(type);
    }

    private String nonBlank(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value.trim();
    }

    private List<Long> normalizeIds(List<Long> ids) {
        if (ids == null) return List.of();
        return ids.stream().filter(Objects::nonNull).distinct().toList();
    }
}
