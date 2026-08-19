package com.orep.backend.service;

import com.orep.backend.dto.DeliberationState;
import com.orep.backend.dto.SubstanceClaim;

import java.util.List;

/**
 * Deliberation lifecycle hangs on Session. Pipeline currentStage stays operational.
 * Default school policy: unconfirmed reports are not final and do not enter student todos.
 */
public final class DeliberationStageMachine {
    public static final String SENSING = "sensing";
    public static final String DRAFT = "draft";
    public static final String VERIFY_CLAIMS = "verify_claims";
    public static final String CHALLENGE = "challenge";
    public static final String AWAIT_TEACHER = "await_teacher";
    public static final String FROZEN = "frozen";
    public static final String CHALLENGE_NOTE = "本场未完成质询";

    private DeliberationStageMachine() {
    }

    public static DeliberationState resolve(Input input) {
        Input safe = input == null ? new Input() : input;
        DeliberationState state = new DeliberationState();
        if (safe.teacherConfirmed) {
            state.setStage(FROZEN);
            state.setTeacherConfirmed(true);
            state.setFinalized(true);
            state.setChallengeIncomplete(!safe.challengeCompleted);
            state.setChallengeNote(safe.challengeCompleted ? "" : CHALLENGE_NOTE);
            state.setHeadline("教师已确认");
            return state;
        }
        String stage = deriveStage(safe);
        boolean challengeIncomplete = !safe.challengeCompleted && (CHALLENGE.equals(stage) || AWAIT_TEACHER.equals(stage));
        state.setStage(stage);
        state.setTeacherConfirmed(false);
        state.setFinalized(false);
        state.setChallengeIncomplete(challengeIncomplete);
        state.setChallengeNote(challengeIncomplete ? CHALLENGE_NOTE : "");
        state.setHeadline(headline(stage, challengeIncomplete));
        return state;
    }

    public static boolean canConfirm(String stage) {
        return VERIFY_CLAIMS.equals(stage) || CHALLENGE.equals(stage) || AWAIT_TEACHER.equals(stage);
    }

    public static boolean studentSeesFinal(DeliberationState state) {
        return state != null && state.isFinalized();
    }

    public static boolean studentSeesTodos(DeliberationState state, boolean taskBookPublished) {
        return studentSeesFinal(state) && taskBookPublished;
    }

    public static boolean pretendedRetrievedCitation(List<SubstanceClaim> claims) {
        if (claims == null) {
            return false;
        }
        for (SubstanceClaim claim : claims) {
            if (claim != null && "retrieved_cited".equals(claim.getClaimStatus())) {
                return true;
            }
        }
        return false;
    }

    private static String deriveStage(Input input) {
        if (!input.hasReport && !input.completed) {
            return SENSING;
        }
        if (!input.completed) {
            return DRAFT;
        }
        if (!input.claimsEvaluated) {
            return VERIFY_CLAIMS;
        }
        if (!input.challengeCompleted) {
            return CHALLENGE;
        }
        return AWAIT_TEACHER;
    }

    private static String headline(String stage, boolean challengeIncomplete) {
        if (FROZEN.equals(stage)) {
            return "教师已确认";
        }
        if (challengeIncomplete) {
            return CHALLENGE_NOTE;
        }
        if (AWAIT_TEACHER.equals(stage)) {
            return "教师未确认";
        }
        if (VERIFY_CLAIMS.equals(stage)) {
            return "本场正在核验";
        }
        if (DRAFT.equals(stage) || SENSING.equals(stage)) {
            return "本场草案尚未完成";
        }
        return "教师未确认";
    }

    public static final class Input {
        public boolean completed;
        public boolean hasReport;
        public boolean claimsEvaluated;
        public boolean challengeCompleted;
        public boolean teacherConfirmed;
    }
}
