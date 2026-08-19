package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.entity.AiJudgePersona;
import com.orep.backend.service.AiJudgePersonaService;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
public class AiJuryPersonaController {
    private final AiJudgePersonaService personaService;

    public AiJuryPersonaController(AiJudgePersonaService personaService) {
        this.personaService = personaService;
    }

    @GetMapping("/api/ai-jury/personas")
    public Result<Map<String, Object>> listUserPersonas() {
        return Result.success(Map.of("personas", personaService.listUserPersonaPayloads()));
    }

    @GetMapping("/api/admin/ai-jury/personas")
    public Result<Map<String, Object>> listAdminPersonas() {
        return Result.success(Map.of("personas", personaService.listAdminPersonaPayloads()));
    }

    @PutMapping("/api/admin/ai-jury/personas/{code}")
    public Result<Map<String, Object>> updatePersona(
            @PathVariable String code,
            @RequestBody Map<String, Object> body
    ) {
        try {
            AiJudgePersona updated = personaService.updatePersona(code, body);
            return Result.success(personaService.toPayload(updated));
        } catch (IllegalArgumentException e) {
            return Result.error(404, e.getMessage());
        }
    }

    @PostMapping("/api/admin/ai-jury/personas/reset")
    public Result<Map<String, Object>> resetDefaults() {
        List<Map<String, Object>> personas = personaService.resetDefaults();
        return Result.success(Map.of("personas", personas));
    }
}
