package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class DeliberationGateReportTest {

    @Test
    void g1LiveGreenOnNewDocketAndLabelStaysForbidden() throws Exception {
        Path root = workspaceRoot();
        DeliberationGateReport.Report report = DeliberationGateReport.evaluate(root);
        DeliberationGateReport.Gate g1 = byId(report, "G1");
        assertEquals(DeliberationGateReport.GREEN, g1.status);
        assertEquals(DeliberationGateReport.GREEN, g1.unitStatus);
        assertEquals(DeliberationGateReport.GREEN, g1.liveStatus);
        assertTrue(g1.detail.contains("43.2"));
        assertTrue(g1.detail.contains("40.9"));
        assertTrue(report.allGreen);
        assertFalse(report.allowRoadshowDeliberationLabel);
        assertFalse(report.reason.contains("评议席已上"));
        assertTrue(report.reason.contains("禁止"));
    }

    @Test
    void runnableGatesAreGreenAndCopyScanIsClean() throws Exception {
        Path root = workspaceRoot();
        DeliberationGateReport.Report report = DeliberationGateReport.evaluate(root);
        for (String id : List.of("G2", "G3", "G4", "G5", "G6", "G7")) {
            assertEquals(DeliberationGateReport.GREEN, byId(report, id).status, id);
        }
        assertTrue(byId(report, "G7").hits.isEmpty());

        Path json = root.resolve("ai-scoring/app/evaluation/deliberation_gate_report.generated.json");
        Path markdown = root.resolve("docs/路演评议席-门禁报告.md");
        Files.createDirectories(json.getParent());
        Files.createDirectories(markdown.getParent());
        new ObjectMapper().writerWithDefaultPrettyPrinter()
                .writeValue(json.toFile(), DeliberationGateReport.toMap(report));
        Files.writeString(markdown, DeliberationGateReport.toMarkdown(report), StandardCharsets.UTF_8);
        assertTrue(Files.size(json) > 0);
        String md = Files.readString(markdown, StandardCharsets.UTF_8);
        assertTrue(md.contains("禁止对外说"));
        assertTrue(md.contains("G1"));
        assertFalse(md.contains("评议席已上线"));
    }

    private static DeliberationGateReport.Gate byId(DeliberationGateReport.Report report, String id) {
        return report.gates.stream().filter(gate -> id.equals(gate.id)).findFirst().orElseThrow();
    }

    private static Path workspaceRoot() {
        Path cwd = Path.of("").toAbsolutePath();
        if (Files.isDirectory(cwd.resolve("frontend")) && Files.isDirectory(cwd.resolve("backend"))) {
            return cwd;
        }
        if (cwd.getFileName() != null && "backend".equals(cwd.getFileName().toString())) {
            return cwd.getParent();
        }
        return cwd;
    }
}
