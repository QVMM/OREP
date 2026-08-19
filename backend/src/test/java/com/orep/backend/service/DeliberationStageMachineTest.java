package com.orep.backend.service;

import com.orep.backend.dto.DeliberationState;
import com.orep.backend.dto.SubstanceClaim;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class DeliberationStageMachineTest {

    @Test
    void incompleteSessionStaysSensingOrDraft() {
        DeliberationStageMachine.Input sensing = new DeliberationStageMachine.Input();
        assertEquals(DeliberationStageMachine.SENSING, DeliberationStageMachine.resolve(sensing).getStage());
        DeliberationStageMachine.Input draft = new DeliberationStageMachine.Input();
        draft.hasReport = true;
        assertEquals(DeliberationStageMachine.DRAFT, DeliberationStageMachine.resolve(draft).getStage());
        assertFalse(DeliberationStageMachine.canConfirm(DeliberationStageMachine.DRAFT));
    }

    @Test
    void completedClaimsWithoutChallengeStayAtChallengeAndStillProduceDraft() {
        DeliberationStageMachine.Input input = readyForTeacher();
        input.challengeCompleted = false;
        DeliberationState state = DeliberationStageMachine.resolve(input);
        assertEquals(DeliberationStageMachine.CHALLENGE, state.getStage());
        assertTrue(state.isChallengeIncomplete());
        assertEquals(DeliberationStageMachine.CHALLENGE_NOTE, state.getChallengeNote());
        assertFalse(state.isFinalized());
        assertTrue(DeliberationStageMachine.canConfirm(state.getStage()));
    }

    @Test
    void unconfirmedDefaultHidesFinalAndStudentTodos() {
        DeliberationState state = DeliberationStageMachine.resolve(readyForTeacher());
        assertEquals(DeliberationStageMachine.AWAIT_TEACHER, state.getStage());
        assertFalse(DeliberationStageMachine.studentSeesFinal(state));
        assertFalse(DeliberationStageMachine.studentSeesTodos(state, true));
        assertEquals("教师未确认", state.getHeadline());
    }

    @Test
    void teacherConfirmFreezesEvenIfChallengeWasIncomplete() {
        DeliberationStageMachine.Input input = readyForTeacher();
        input.challengeCompleted = false;
        input.teacherConfirmed = true;
        DeliberationState state = DeliberationStageMachine.resolve(input);
        assertEquals(DeliberationStageMachine.FROZEN, state.getStage());
        assertTrue(state.isFinalized());
        assertTrue(state.isChallengeIncomplete());
        assertTrue(DeliberationStageMachine.studentSeesFinal(state));
        assertTrue(DeliberationStageMachine.studentSeesTodos(state, true));
        assertFalse(DeliberationStageMachine.studentSeesTodos(state, false));
    }

    @Test
    void verifyClaimsMustNotPretendRetrievedCitation() {
        SubstanceClaim cited = new SubstanceClaim();
        cited.setClaimType("wrapper");
        cited.setClaimStatus("retrieved_cited");
        assertTrue(DeliberationStageMachine.pretendedRetrievedCitation(List.of(cited)));
        SubstanceClaim seen = new SubstanceClaim();
        seen.setClaimType("wrapper");
        seen.setClaimStatus("seen_in_session");
        assertFalse(DeliberationStageMachine.pretendedRetrievedCitation(List.of(seen)));
    }

    private static DeliberationStageMachine.Input readyForTeacher() {
        DeliberationStageMachine.Input input = new DeliberationStageMachine.Input();
        input.completed = true;
        input.hasReport = true;
        input.claimsEvaluated = true;
        input.challengeCompleted = true;
        return input;
    }
}
