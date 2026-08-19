package com.orep.backend.service;

import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.entity.TrackRubricConfig;
import org.springframework.stereotype.Service;

@Service
public class RubricResolverService {
    private final TrackRubricConfigService rubricConfigService;
    private final TrackEvidenceSchemaService evidenceSchemaService;

    public RubricResolverService(TrackRubricConfigService rubricConfigService,
                                 TrackEvidenceSchemaService evidenceSchemaService) {
        this.rubricConfigService = rubricConfigService;
        this.evidenceSchemaService = evidenceSchemaService;
    }

    public ResolvedRubric resolve(String trackId, String trackName) {
        TrackRubricConfig rubric = rubricConfigService.resolveActive(trackId, trackName);
        TrackEvidenceSchema schema;
        try {
            schema = evidenceSchemaService.resolveActive(rubric.getTrackId(), rubric.getTrackName());
        } catch (IllegalStateException e) {
            if (e.getMessage() == null || !e.getMessage().contains("未找到启用证据结构")) {
                throw e;
            }
            schema = evidenceSchemaService.generatedSchema(rubric.getTrackId(), rubric.getTrackName());
        }

        ResolvedRubric resolved = new ResolvedRubric();
        resolved.setRubricId(rubric.getRubricId());
        resolved.setRubricInternalVersion(rubric.getInternalVersion());
        resolved.setRubricHash(rubric.getRubricHash());
        resolved.setRubricPath(rubric.getRubricPath());
        resolved.setTrackId(rubric.getTrackId());
        resolved.setTrackName(rubric.getTrackName());
        resolved.setEvidenceSchemaId(schema.getId());
        resolved.setEvidenceSchemaVersion(schema.getSchemaVersion());
        resolved.setEvidenceSchemaHash(schema.getSchemaHash());
        resolved.setMaterialTypesJson(schema.getMaterialTypesJson());
        resolved.setFrameTargetsJson(schema.getFrameTargetsJson());
        resolved.setDemoActionsJson(schema.getDemoActionsJson());
        resolved.setRiskPatternsJson(schema.getRiskPatternsJson());
        resolved.setThirdPartyPackagingSignalsJson(schema.getThirdPartyPackagingSignalsJson());
        resolved.setAcceptableEvidenceLevelsJson(schema.getAcceptableEvidenceLevelsJson());
        return resolved;
    }
}
