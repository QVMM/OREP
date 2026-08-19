package com.orep.backend.service.roadshow;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.entity.Script;
import com.orep.backend.service.ScriptScoreRevisePlanner;
import com.orep.backend.service.ScriptScoreReviseService;
import com.orep.backend.service.ScriptService;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class JudgePathService {

    private final ScriptService scripts;
    private final ScriptScoreReviseService scoreBrief;
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;

    public JudgePathService(
            ScriptService scripts,
            ScriptScoreReviseService scoreBrief,
            JdbcTemplate jdbc,
            ObjectMapper mapper
    ) {
        this.scripts = scripts;
        this.scoreBrief = scoreBrief;
        this.jdbc = jdbc;
        this.mapper = mapper;
    }

    public Map<String, Object> scriptMeter(Long scriptId, Long userId) {
        return scripts.pageMeter(scriptId, userId);
    }

    public Map<String, Object> compile(Long scriptId, Long userId, Long tenantId) {
        Script script = scripts.getById(scriptId, userId);
        if (script == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "讲稿不存在或无权访问");
        }
        script = scripts.hydrateFromSmartDoc(script, userId);
        List<Map<String, Object>> steps = ScriptScoreRevisePlanner.flattenSteps(script.getContent());
        Map<String, Object> brief = scoreBrief.brief(scriptId, userId, tenantId);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = brief.get("diagnosis") instanceof List<?> d
                ? (List<Map<String, Object>>) d : List.of();
        List<Map<String, Object>> tokens = EvidenceTokenizer.extract(steps);
        Map<String, Object> compiled = JudgePathCompiler.compile(steps, items, tokens);
        compiled.put("scriptId", scriptId);
        compiled.put("scriptTitle", script.getTitle());
        compiled.put("contentVersion", versionOf(script.getContentVersion()));
        compiled.put("scoreReportId", brief.get("scoreReportId"));
        compiled.put("canPrint", JudgePathGates.canPrint(compiled));
        compiled.putAll(scripts.pageMeter(scriptId, userId));

        String json = write(compiled);
        jdbc.update(
                """
                INSERT INTO judge_path (created_by, script_id, score_report_id, script_content_version, status, path_json)
                VALUES (?, ?, ?, ?, 'compiled', ?)
                """,
                userId,
                scriptId,
                asLong(brief.get("scoreReportId")),
                versionOf(script.getContentVersion()),
                json
        );
        Long id = jdbc.queryForObject("SELECT LAST_INSERT_ID()", Long.class);
        compiled.put("id", id);
        compiled.put("status", "compiled");
        return compiled;
    }

    public Map<String, Object> get(Long id, Long userId) {
        List<Map<String, Object>> rows = jdbc.queryForList(
                "SELECT id, created_by, status, path_json FROM judge_path WHERE id = ?", id);
        if (rows.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "路径不存在");
        }
        Map<String, Object> row = rows.get(0);
        if (!userId.equals(asLong(row.get("created_by")))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "路径不存在");
        }
        Map<String, Object> path = read(String.valueOf(row.get("path_json")));
        path.put("id", asLong(row.get("id")));
        path.put("status", row.get("status"));
        path.put("canPrint", JudgePathGates.canPrint(path));
        return path;
    }

    public Map<String, Object> ackHole(Long id, Long userId, String holeId) {
        Map<String, Object> path = get(id, userId);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> holes = (List<Map<String, Object>>) path.get("holes");
        if (holes != null) {
            for (Map<String, Object> h : holes) {
                if (holeId != null && holeId.equals(String.valueOf(h.get("id")))) {
                    h.put("acked", true);
                }
            }
        }
        saveRevision(id, userId, path);
        return path;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> print(Long id, Long userId) {
        Map<String, Object> path = get(id, userId);
        if (!JudgePathGates.canPrint(path)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "还有内容没有出处，先决定这场写不写进 PPT");
        }
        List<Map<String, Object>> props = path.get("propositions") instanceof List<?> p
                ? (List<Map<String, Object>>) p : List.of();
        List<Map<String, Object>> pages = PageTypePlanner.plan(props);
        if (pages.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "没有可做成页的内容");
        }
        byte[] pptx;
        try {
            pptx = RoadshowPptxWriter.write(pages);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "做成 PPT 失败");
        }
        Path file = pptxFile(id);
        try {
            Files.createDirectories(file.getParent());
            Files.write(file, pptx);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "保存 PPT 失败");
        }
        path.put("printPages", pages);
        path.put("pptxPath", file.toString());
        saveRevision(id, userId, path);
        jdbc.update("UPDATE judge_path SET status = 'printed' WHERE id = ?", id);
        path.put("status", "printed");
        path.put("canPrint", true);
        return path;
    }

    public byte[] download(Long id, Long userId) {
        Map<String, Object> path = get(id, userId);
        Object stored = path.get("pptxPath");
        Path file = stored == null || String.valueOf(stored).isBlank() ? pptxFile(id) : Path.of(String.valueOf(stored));
        if (!Files.isRegularFile(file)) {
            path = print(id, userId);
            stored = path.get("pptxPath");
            file = stored == null ? pptxFile(id) : Path.of(String.valueOf(stored));
        }
        try {
            return Files.readAllBytes(file);
        } catch (IOException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "下载失败");
        }
    }

    public String downloadName(Map<String, Object> path) {
        String title = path == null ? "" : String.valueOf(path.getOrDefault("scriptTitle", "路演"));
        if (title.isBlank() || "null".equals(title)) title = "路演";
        return title.replaceAll("[\\\\/:*?\"<>|]", "_") + " · 路演台.pptx";
    }

    private static Path pptxFile(Long id) {
        return Path.of("uploads", "roadshow", id + ".pptx");
    }

    public Map<String, Object> attachDeck(Long id, Long userId, Long deckId, LegacyDeckService decks) {
        decks.resetWork(deckId, userId);
        Map<String, Object> path = get(id, userId);
        Map<String, Object> deck = decks.get(deckId, userId);
        path.put("legacyDeck", deck);
        saveRevision(id, userId, path);
        jdbc.update("UPDATE judge_path SET legacy_deck_id = ? WHERE id = ?", deckId, id);
        return path;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> align(Long id, Long userId, LegacyDeckService decks) {
        Map<String, Object> path = get(id, userId);
        Map<String, Object> deckMeta = path.get("legacyDeck") instanceof Map<?, ?> m
                ? (Map<String, Object>) m : Map.of();
        Long deckId = asLong(deckMeta.get("id"));
        if (deckId == null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "还没有交 PPT。先把这份拖进来。");
        }
        Map<String, Object> deck = decks.pages(deckId, userId);
        List<Map<String, Object>> props = path.get("propositions") instanceof List<?> p
                ? (List<Map<String, Object>>) p : List.of();
        List<Map<String, Object>> pages = deck.get("pages") instanceof List<?> pg
                ? (List<Map<String, Object>>) pg : List.of();
        List<Map<String, Object>> rows = LegacyAligner.align(props, pages);
        for (Map<String, Object> page : pages) {
            Object n = page.get("page");
            Map<String, Object> hit = rows.stream()
                    .filter(r -> n != null && n.equals(r.get("page")))
                    .min(java.util.Comparator.comparingInt(r -> actionRank(r.get("action"))))
                    .orElse(null);
            if (hit == null) {
                page.put("action", "hold");
                page.put("actionLabel", "先不动");
                page.put("why", "暂时对不上讲稿。先留着。");
                page.put("aiWill", "先不改。");
                continue;
            }
            page.put("action", hit.get("action"));
            page.put("actionLabel", hit.get("actionLabel"));
            page.put("why", hit.get("why"));
            page.put("aiWill", hit.get("aiWill"));
            page.put("spoken", hit.get("spoken"));
            page.put("willTitle", hit.get("willTitle"));
            page.put("willNumber", hit.get("willNumber"));
            page.put("willLine", hit.get("willLine"));
            page.put("title", hit.get("title"));
            page.put("applied", false);
        }
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("pathId", id);
        view.put("scriptTitle", path.get("scriptTitle"));
        view.put("deck", deck);
        view.put("rows", rows);
        view.put("todo", rows.stream().filter(r -> !"hold".equals(r.get("action"))).count());
        int scriptPages = asInt(path.get("scriptPageCount"));
        if (scriptPages == 0) {
            Long scriptId = asLong(path.get("scriptId"));
            if (scriptId != null) {
                Map<String, Object> meter = scripts.pageMeter(scriptId, userId);
                view.putAll(meter);
                scriptPages = asInt(meter.get("scriptPageCount"));
            }
        } else {
            view.put("scriptPageCount", scriptPages);
            view.put("pageHealth", path.get("pageHealth"));
            view.put("pageHealthLabel", path.get("pageHealthLabel"));
        }
        int deckPages = asInt(deck.get("pageCount"));
        if (deckPages == 0 && deck.get("pages") instanceof List<?> pg) deckPages = pg.size();
        view.put("deckPageCount", deckPages);
        view.put("deckHealth", com.orep.backend.service.ScriptSdocCodec.pageHealth(deckPages));
        view.put("deckHealthLabel", com.orep.backend.service.ScriptSdocCodec.pageHealthLabel(deckPages));
        return view;
    }

    public Map<String, Object> confirm(Long id, Long userId) {
        Map<String, Object> path = get(id, userId);
        if (!JudgePathGates.canPrint(path)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "还有内容没有出处，先决定这场写不写进 PPT");
        }
        saveRevision(id, userId, path);
        jdbc.update("UPDATE judge_path SET status = 'confirmed' WHERE id = ?", id);
        path.put("status", "confirmed");
        path.put("canPrint", true);
        return path;
    }

    private void saveRevision(Long id, Long userId, Map<String, Object> path) {
        String json = write(path);
        jdbc.update("INSERT INTO judge_path_revision (path_id, path_json, created_by) VALUES (?, ?, ?)",
                id, json, userId);
        jdbc.update("UPDATE judge_path SET path_json = ? WHERE id = ?", json, id);
    }

    private String write(Map<String, Object> path) {
        try {
            return mapper.writeValueAsString(path);
        } catch (JsonProcessingException e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "路径无法保存");
        }
    }

    private Map<String, Object> read(String json) {
        try {
            return mapper.readValue(json, new TypeReference<LinkedHashMap<String, Object>>() {});
        } catch (Exception e) {
            return new LinkedHashMap<>();
        }
    }

    private static int versionOf(Integer version) {
        return version == null || version < 1 ? 1 : version;
    }

    private static int actionRank(Object action) {
        return switch (String.valueOf(action)) {
            case "edit" -> 0;
            case "replace" -> 1;
            case "drop" -> 2;
            case "add" -> 3;
            default -> 9;
        };
    }

    private static int asInt(Object v) {
        if (v == null || "".equals(v)) return 0;
        if (v instanceof Number n) return n.intValue();
        try {
            return Integer.parseInt(String.valueOf(v));
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private static Long asLong(Object v) {
        if (v == null) return null;
        if (v instanceof Number n) return n.longValue();
        try {
            return Long.parseLong(String.valueOf(v));
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
