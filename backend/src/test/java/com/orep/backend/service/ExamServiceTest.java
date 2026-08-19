package com.orep.backend.service;

import com.orep.backend.dto.ExamQuestionRequest;
import com.orep.backend.entity.ExamAttempt;
import com.orep.backend.entity.ExamPaper;
import com.orep.backend.entity.ExamPaperQuestion;
import com.orep.backend.entity.ExamQuestion;
import com.orep.backend.mapper.ExamAttemptAnswerMapper;
import com.orep.backend.mapper.ExamAttemptMapper;
import com.orep.backend.mapper.ExamFavoriteMapper;
import com.orep.backend.mapper.ExamPaperMapper;
import com.orep.backend.mapper.ExamPaperQuestionMapper;
import com.orep.backend.mapper.ExamQuestionMapper;
import com.orep.backend.mapper.ExamWrongQuestionMapper;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class ExamServiceTest {

    @Test
    void createQuestionStoresAnswerButStudentViewDoesNotExposeIt() {
        ExamQuestionMapper questionMapper = mock(ExamQuestionMapper.class);
        ExamService service = service(questionMapper, null, null, null, null, null, null);
        ExamQuestionRequest request = new ExamQuestionRequest();
        request.setQuestionType("single");
        request.setStem("RAG 的核心能力是什么？");
        request.setOptionsJson("[{\"key\":\"A\",\"text\":\"检索增强生成\"}]");
        request.setAnswerJson("[\"A\"]");
        request.setAnalysis("RAG 通过检索补充上下文。");
        request.setScore(5);

        ExamQuestion question = service.createQuestion(request, 8L);

        assertThat(question.getAnswerJson()).isEqualTo("[\"A\"]");
        assertThat(question.getCreatedBy()).isEqualTo(8L);
        assertThat(service.toStudentQuestion(question).getAnswerJson()).isNull();
        assertThat(service.toStudentQuestion(question).getAnalysis()).isNull();
        verify(questionMapper).insert(question);
    }

    @Test
    void submitAttemptScoresObjectiveQuestionsAndRecordsWrongQuestion() {
        ExamQuestionMapper questionMapper = mock(ExamQuestionMapper.class);
        ExamPaperQuestionMapper paperQuestionMapper = mock(ExamPaperQuestionMapper.class);
        ExamAttemptMapper attemptMapper = mock(ExamAttemptMapper.class);
        ExamAttemptAnswerMapper answerMapper = mock(ExamAttemptAnswerMapper.class);
        ExamWrongQuestionMapper wrongMapper = mock(ExamWrongQuestionMapper.class);
        ExamPaperMapper paperMapper = mock(ExamPaperMapper.class);
        ExamService service = service(questionMapper, paperMapper, paperQuestionMapper, attemptMapper, answerMapper, wrongMapper, null);

        ExamAttempt attempt = new ExamAttempt();
        attempt.setId(9L);
        attempt.setPaperId(3L);
        attempt.setUserId(8L);
        attempt.setStatus("in_progress");
        when(attemptMapper.selectById(9L)).thenReturn(attempt);
        ExamPaper paper = new ExamPaper();
        paper.setId(3L);
        paper.setPassScore(6);
        when(paperMapper.selectById(3L)).thenReturn(paper);

        ExamQuestion single = question(1L, "single", "[\"A\"]", 5);
        ExamQuestion multi = question(2L, "multiple", "[\"A\",\"C\"]", 5);
        ExamPaperQuestion firstLink = paperQuestion(1L, 5, 10);
        ExamPaperQuestion secondLink = paperQuestion(2L, 5, 20);
        when(paperQuestionMapper.selectList(any())).thenReturn(List.of(firstLink, secondLink));
        when(questionMapper.selectBatchIds(any())).thenReturn(List.of(single, multi));
        when(answerMapper.selectList(any())).thenReturn(List.of());

        var result = service.submitAttempt(8L, 9L, java.util.Map.of(
                1L, "[\"A\"]",
                2L, "[\"A\",\"B\"]"
        ));

        assertThat(result.getScore()).isEqualTo(5);
        assertThat(result.getPassed()).isFalse();
        assertThat(result.getWrongQuestions()).hasSize(1);
        assertThat(result.getWrongQuestions().get(0).getQuestionId()).isEqualTo(2L);
        verify(attemptMapper).updateById(attempt);
        verify(wrongMapper).insert(any());
    }

    private ExamService service(
            ExamQuestionMapper questionMapper,
            ExamPaperMapper paperMapper,
            ExamPaperQuestionMapper paperQuestionMapper,
            ExamAttemptMapper attemptMapper,
            ExamAttemptAnswerMapper answerMapper,
            ExamWrongQuestionMapper wrongMapper,
            ExamFavoriteMapper favoriteMapper
    ) {
        return new ExamService(questionMapper, paperMapper, paperQuestionMapper, attemptMapper, answerMapper, wrongMapper, favoriteMapper, null);
    }

    private ExamQuestion question(Long id, String type, String answerJson, Integer score) {
        ExamQuestion question = new ExamQuestion();
        question.setId(id);
        question.setQuestionType(type);
        question.setStem("题目" + id);
        question.setOptionsJson("[]");
        question.setAnswerJson(answerJson);
        question.setScore(score);
        return question;
    }

    private ExamPaperQuestion paperQuestion(Long questionId, Integer score, Integer sortOrder) {
        ExamPaperQuestion paperQuestion = new ExamPaperQuestion();
        paperQuestion.setPaperId(3L);
        paperQuestion.setQuestionId(questionId);
        paperQuestion.setScore(score);
        paperQuestion.setSortOrder(sortOrder);
        return paperQuestion;
    }
}
