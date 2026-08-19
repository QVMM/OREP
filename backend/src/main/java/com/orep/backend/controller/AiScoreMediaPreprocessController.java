package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreMediaPreprocessService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@RestController
@RequestMapping("/api/ai-score/preprocess-jobs")
public class AiScoreMediaPreprocessController {
    private final AiScoreMediaPreprocessService preprocessService;
    private final AiScoreAccessControlService accessControlService;

    public AiScoreMediaPreprocessController(AiScoreMediaPreprocessService preprocessService,
                                            AiScoreAccessControlService accessControlService) {
        this.preprocessService = preprocessService;
        this.accessControlService = accessControlService;
    }

    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public Result<Map<String, Object>> create(
            @RequestParam(value = "projectId", required = false) Long projectId,
            @RequestParam(value = "teamId", required = false) Long teamId,
            @RequestParam(value = "trackId", required = false) String trackId,
            @RequestParam(value = "trackName", required = false) String trackName,
            @RequestParam(value = "useHistoryMemory", defaultValue = "true") Boolean useHistoryMemory,
            @RequestParam(value = "juryEnabled", defaultValue = "false") Boolean juryEnabled,
            @RequestParam(value = "video", required = false) MultipartFile video,
            HttpServletRequest request) {
        Long userId = attrLong(request, "userId");
        accessControlService.assertTeamAccess(teamId, attrLong(request, "tenantId"), userId, attrString(request, "role"));
        return Result.success(preprocessService.createJob(
                video,
                projectId,
                teamId,
                trackId,
                trackName,
                useHistoryMemory,
                juryEnabled,
                userId
        ));
    }

    @GetMapping("/{jobId}")
    public Result<Map<String, Object>> status(@PathVariable Long jobId, HttpServletRequest request) {
        try {
            return Result.success(preprocessService.status(jobId, attrLong(request, "userId")));
        } catch (IllegalStateException e) {
            return Result.error(404, e.getMessage());
        }
    }

    private Long attrLong(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value instanceof Number number ? number.longValue() : null;
    }

    private String attrString(HttpServletRequest request, String key) {
        Object value = request.getAttribute(key);
        return value == null ? null : String.valueOf(value);
    }
}
