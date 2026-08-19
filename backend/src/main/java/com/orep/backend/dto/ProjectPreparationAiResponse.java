package com.orep.backend.dto;

import lombok.Data;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Data
public class ProjectPreparationAiResponse {
    private boolean accepted;
    private String message;
    private String assistantMessage;
    private List<AgentStep> agentSteps = new ArrayList<>();
    private List<String> questions = new ArrayList<>();
    private String researchSummary;
    private List<Direction> directions = new ArrayList<>();
    private List<Map<String, Object>> sources = new ArrayList<>();
    private List<String> nextActions = new ArrayList<>();
    private String model;

    public void setAgentSteps(List<AgentStep> agentSteps) {
        this.agentSteps = emptyIfNull(agentSteps);
    }

    public void setQuestions(List<String> questions) {
        this.questions = emptyIfNull(questions);
    }

    public void setDirections(List<Direction> directions) {
        this.directions = emptyIfNull(directions);
    }

    public void setSources(List<Map<String, Object>> sources) {
        this.sources = emptyIfNull(sources);
    }

    public void setNextActions(List<String> nextActions) {
        this.nextActions = emptyIfNull(nextActions);
    }

    private static <T> List<T> emptyIfNull(List<T> value) {
        return value == null ? new ArrayList<>() : value;
    }

    @Data
    public static class Direction {
        private String title;
        private String summary;
        private List<String> tags = new ArrayList<>();
        private String equipmentMatch;
        private String competitionMatch;
        private String recommendationLevel;
        private String expertRationale;
        private DirectionScore scores;
        private List<String> evidenceGaps = new ArrayList<>();
        private List<String> risks = new ArrayList<>();
        private List<Map<String, Object>> nextTasks = new ArrayList<>();
        private List<Map<String, Object>> researchRefs = new ArrayList<>();

        public void setTags(List<String> tags) {
            this.tags = emptyIfNull(tags);
        }

        public void setEvidenceGaps(List<String> evidenceGaps) {
            this.evidenceGaps = emptyIfNull(evidenceGaps);
        }

        public void setRisks(List<String> risks) {
            this.risks = emptyIfNull(risks);
        }

        public void setNextTasks(List<Map<String, Object>> nextTasks) {
            this.nextTasks = emptyIfNull(nextTasks);
        }

        public void setResearchRefs(List<Map<String, Object>> researchRefs) {
            this.researchRefs = emptyIfNull(researchRefs);
        }
    }

    @Data
    public static class AgentStep {
        private String agentKey;
        private String agentName;
        private String agentRole;
        private String status;
        private String inputSummary;
        private String outputSummary;
        private List<String> findings = new ArrayList<>();
        private List<String> questions = new ArrayList<>();
        private List<Map<String, Object>> sources = new ArrayList<>();

        public void setFindings(List<String> findings) {
            this.findings = emptyIfNull(findings);
        }

        public void setQuestions(List<String> questions) {
            this.questions = emptyIfNull(questions);
        }

        public void setSources(List<Map<String, Object>> sources) {
            this.sources = emptyIfNull(sources);
        }
    }

    @Data
    public static class DirectionScore {
        private Integer competitionFit;
        private Integer resourceFit;
        private Integer innovation;
        private Integer demoReadiness;
        private Integer riskControl;
    }
}
