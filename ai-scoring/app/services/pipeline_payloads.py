"""Helpers for storing scoring pipeline payloads."""

import hashlib
import json
import re

from app.services.evidence_extraction_service import load_pilot_track_rule
from app.services.scoring.rule_executor import execute_rule_score


def persistable_video_analysis(video_analysis: dict) -> dict:
    """Build the video payload stored in result_*.json without dropping frame evidence."""
    return {
        'frame_count': video_analysis['frame_count'],
        'interval_sec': video_analysis.get('interval_sec'),
        'per_frame': video_analysis.get('per_frame', []),
        'aggregates': video_analysis.get('aggregates', {}),
        'tokens_used': video_analysis.get('tokens_used', {}),
        'source': video_analysis.get('source', 'video_file'),
        'captured_frame_count': video_analysis.get('captured_frame_count'),
        'selected_frame_count': video_analysis.get('selected_frame_count'),
        'selection_strategy': video_analysis.get('selection_strategy', {}),
    }


def persistable_fusion(fused_data: dict) -> dict:
    """Build the fusion payload stored in result_*.json for charts and evidence views."""
    return {
        'summary': fused_data.get('summary', {}),
        'audio_windows': fused_data.get('audio_windows', []),
        'contradictions': fused_data.get('contradictions', []),
        'trends': fused_data.get('trends', {}),
        'timeline': fused_data.get('timeline', []),
        'screen_content_summary': fused_data.get('screen_content_summary', {}),
    }


def validate_video_analysis_for_scoring(video_analysis: dict, min_valid_ratio: float = 0.6) -> None:
    """Ensure a video scoring run has real visual model output."""
    aggregates = video_analysis.get('aggregates') or {}
    per_frame = video_analysis.get('per_frame') or []
    valid_frames = [
        frame for frame in per_frame
        if isinstance(frame, dict) and 'error' not in frame
    ]
    if aggregates.get('error') or not valid_frames:
        sample_errors = [
            str(frame.get('error'))
            for frame in per_frame
            if isinstance(frame, dict) and frame.get('error')
        ][:3]
        suffix = f"；示例错误：{' | '.join(sample_errors)}" if sample_errors else ""
        raise RuntimeError(f"视频帧分析没有有效结果，已停止评分{suffix}")
    total_frames = len(per_frame)
    if total_frames and len(valid_frames) / total_frames < min_valid_ratio:
        raise RuntimeError(
            f"视频帧分析有效率过低，已停止评分：有效 {len(valid_frames)}/{total_frames} 帧"
        )


def validate_fusion_for_scoring(fused_data: dict) -> None:
    """Ensure audio/video fusion has timeline points for charts and evidence review."""
    timeline = fused_data.get('timeline') or []
    summary = fused_data.get('summary') or {}
    if not timeline or int(summary.get('total_windows') or 0) <= 0:
        raise RuntimeError("音视频融合没有生成有效时间线，已停止评分")


def build_backend_callback_payload(meeting_id: str, result: dict) -> dict:
    """Build the Spring callback payload from a completed scoring result.

    When evidence extraction is present, overallScore only comes from the
    structured rule engine. LLM totals are exposed as llmRawScore only.
    """
    ai_score = result.get('ai_score', {}) or {}
    llm_score = ai_score.get('overall_score')
    payload = {
        'meetingId': meeting_id,
        'status': result.get('status'),
        'overallScore': llm_score if llm_score is not None else 0,
        'resultPath': f"results/result_{meeting_id}.json",
        'reportUrl': f'/api/ai/report/{meeting_id}',
        'model': ai_score.get('model', ''),
        'transcript': result.get('asr', {}).get('transcript', ''),
        'hasVideo': result.get('has_video', False),
        'llmRawScore': ai_score.get('raw_overall_score', llm_score),
        'scoreAuthority': 'legacy_llm',
    }

    if 'dimensions' in ai_score:
        payload['dimensions'] = ai_score['dimensions']
    if 'highlights' in ai_score:
        payload['highlights'] = ai_score['highlights']
    if 'critical_issues' in ai_score:
        payload['criticalIssues'] = ai_score['critical_issues']
    if 'improvement_priorities' in ai_score:
        payload['improvementPriorities'] = ai_score['improvement_priorities']
    if 'score_calibration' in result:
        payload['scoreCalibration'] = result['score_calibration']

    evidence_extraction = result.get('evidence_extraction') or {}
    if evidence_extraction:
        payload['evidenceExtraction'] = _without_llm_scores(evidence_extraction)
        extraction_quality = evidence_extraction.get('extractionQuality') or {}
        extraction_not_publishable = (
            evidence_extraction.get('status') in {'failed', 'review_required'}
            or extraction_quality.get('publicationEligible') is False
        )
        if extraction_not_publishable:
            payload['overallScore'] = None
            payload['scoreAuthority'] = 'review_required'
            payload['reviewReason'] = 'evidence_extraction_not_publishable'
            payload['dimensions'] = {}
        else:
            rule_payload = build_rule_engine_shadow_payload(result)
            payload.update(rule_payload)
            if rule_payload.get('scoreAuthority') == 'structured_rule_engine':
                payload['overallScore'] = rule_payload.get('finalScore')
                payload['scoreAuthority'] = 'structured_rule_engine'
                if rule_payload.get('dimensionScores'):
                    payload['dimensions'] = {
                        code: {
                            'score': score,
                            'max_score': (rule_payload.get('dimensionMaxScores') or {}).get(code),
                            'source': 'structured_rule_engine',
                        }
                        for code, score in (rule_payload.get('dimensionScores') or {}).items()
                    }
            else:
                # Extraction present but rule score missing: do not publish LLM total.
                payload['overallScore'] = None
                payload['scoreAuthority'] = 'review_required'
                payload['reviewReason'] = 'rule_engine_score_unavailable'
                payload['dimensions'] = {}

    duration_s = result.get('asr', {}).get('duration', 0)
    if duration_s > 0:
        payload['durationMinutes'] = round(duration_s / 60, 1)

    if 'speech_quality' in result:
        payload['speechQuality'] = result['speech_quality']
    if 'fusion' in result:
        payload['fusionSummary'] = result.get('fusion', {}).get('summary', {})
    if 'speaker_evidence' in result:
        payload['speakerEvidence'] = result.get('speaker_evidence') or []
    speaker_attribution = (result.get('asr') or {}).get('speakerAttribution')
    if isinstance(speaker_attribution, dict):
        payload['speakerAttribution'] = speaker_attribution

    return payload


def build_rule_engine_shadow_payload(result: dict) -> dict:
    evidence_extraction = result.get('evidence_extraction') or {}
    track_rule = _load_shadow_track_rule(evidence_extraction)
    observation_rules = {
        item.get('observationCode'): item
        for item in (track_rule.get('observations') if track_rule else []) or []
        if isinstance(item, dict) and item.get('observationCode')
    }
    evidence_anchors, evidence_anchor_ids = _build_shadow_evidence_anchors(
        evidence_extraction.get('evidenceItems') or []
    )
    asr_result = result.get('asr') if isinstance(result.get('asr'), dict) else {}
    llm_observations = _build_shadow_observations(
        evidence_extraction.get('observationEvidence') or [],
        observation_rules,
        evidence_anchor_ids,
    )
    model_review_score = None
    try:
        model_review_score = execute_rule_score(llm_observations, []).get('finalScore')
    except Exception:
        model_review_score = None
    if track_rule and asr_result:
        from app.services.scoring.tape_grounded_labels import apply_tape_grounded_labels

        evidence_extraction = apply_tape_grounded_labels(
            evidence_extraction,
            asr_result,
            track_rule,
        )
        result['evidence_extraction'] = evidence_extraction
    observations = _build_shadow_observations(
        evidence_extraction.get('observationEvidence') or [],
        observation_rules,
        evidence_anchor_ids,
    )
    all_deductions = _build_shadow_deductions(
        evidence_extraction.get('deductionCandidates') or [],
        observation_rules,
        evidence_extraction.get('recoveryCandidates') or [],
    )
    for deduction in all_deductions:
        deduction['evidenceAnchorIds'] = _anchor_ids_for_evidence_ids(
            deduction.get('evidenceIds') or [],
            evidence_anchor_ids,
        )
    deductions = [
        item for item in all_deductions
        if item.get('scoreEffect') == 'subtractive'
    ]
    diagnostic_deductions = [
        item for item in all_deductions
        if item.get('scoreEffect') != 'subtractive'
    ]
    authoritative = execute_rule_score(observations, deductions)
    # 权威分已按转写+量表钉死。禁止再用历史场次把分往上次 LLM 结果上拽。
    observations = authoritative['observations']
    for observation in observations:
        observation['rawScore'] = observation.get('baseScore')
    _enrich_evidence_anchors_with_score_links(
        evidence_anchors,
        observations=observations,
        deductions=deductions,
        loss_ledger=authoritative.get('lossLedger') or [],
    )

    ai_score = result.get('ai_score') or {}
    official_score = _safe_float(ai_score.get('overall_score'))
    llm_raw_score = _safe_float(ai_score.get('raw_overall_score'), official_score)
    rule_engine_score = authoritative['finalScore']
    score_diff = round(rule_engine_score - official_score, 2)
    diff_reasons = []
    if abs(score_diff) > 10:
        diff_reasons.append('score_diff_exceeds_10')
    if any(item.get('evidenceLevel') in {'E0', 'E1'} for item in observations):
        diff_reasons.append('low_evidence_level_present')
    if authoritative.get('_stability_clamp'):
        diff_reasons.append('cross_session_stability_clamp')

    payload = {
        'scoreAuthority': authoritative['scoreAuthority'],
        'scorePolicyVersion': authoritative['scorePolicyVersion'],
        'finalScore': authoritative['finalScore'],
        'baseScore': authoritative['baseScore'],
        'performanceGap': authoritative['performanceGap'],
        'evidenceLimitedGap': authoritative['evidenceLimitedGap'],
        'deductedScore': authoritative['deductedScore'],
        'recoveredScore': authoritative['recoveredScore'],
        'effectiveHardPenalty': authoritative['effectiveHardPenalty'],
        'currentScoreCap': authoritative['currentScoreCap'],
        'dimensionScores': authoritative['dimensionScores'],
        'dimensionMaxScores': authoritative['dimensionMaxScores'],
        'reconciliation': authoritative['reconciliation'],
        'llmRawScore': llm_raw_score,
        'modelReviewScore': model_review_score,
        'tapeGrounded': True,
        'ruleEngineScore': rule_engine_score,
        'scoreDiff': score_diff,
        'diffReasons': diff_reasons,
        'ruleEngineVersion': 'score-policy-v2-single-attribution',
        **_scoring_identity(result, evidence_extraction),
        'competitionBinding': result.get('competition_binding'),
        'observations': observations,
        'deductions': deductions,
        'diagnosticDeductions': diagnostic_deductions,
        'lossLedger': authoritative['lossLedger'],
        'evidenceAnchors': evidence_anchors,
    }
    if authoritative.get('_stability_clamp'):
        payload['stabilityClamp'] = authoritative['_stability_clamp']
    return payload


def _load_shadow_track_rule(evidence_extraction):
    track = (
        evidence_extraction.get('trackName')
        or evidence_extraction.get('trackId')
        or evidence_extraction.get('track')
    )
    if not track:
        return None
    try:
        return load_pilot_track_rule(str(track))
    except Exception:
        return None


def _scoring_identity(result, evidence_extraction):
    """Build rule / evidence / instance fingerprints.

    - ruleFingerprint / scoringFingerprint: rule + competition identity
      (backward-compatible key used by loss ledger seeds)
    - evidenceSnapshotHash: this round's evidence inventory + levels
    - scoreInstanceId: one concrete scoring run (rule + evidence + policy)
    """
    rule_fingerprint = _rule_fingerprint(result, evidence_extraction)
    evidence_snapshot_hash = _evidence_snapshot_hash(evidence_extraction)
    score_instance_id = _stable_hex({
        'ruleFingerprint': rule_fingerprint,
        'evidenceSnapshotHash': evidence_snapshot_hash,
        'scorePolicyVersion': 'score-policy-v2-single-attribution',
    })
    return {
        'scoringFingerprint': rule_fingerprint,
        'ruleFingerprint': rule_fingerprint,
        'evidenceSnapshotHash': evidence_snapshot_hash,
        'scoreInstanceId': score_instance_id,
    }


def _scoring_fingerprint(result, evidence_extraction):
    """Backward-compatible alias for the rule identity fingerprint."""
    return _rule_fingerprint(result, evidence_extraction)


def _rule_fingerprint(result, evidence_extraction):
    canonical = {
        'scorePolicyVersion': 'score-policy-v2-single-attribution',
        'ruleVersion': evidence_extraction.get('ruleVersion'),
        'ruleHash': evidence_extraction.get('ruleHash'),
        'competitionBinding': result.get('competition_binding') or {},
    }
    return _stable_hex(canonical)


def _evidence_snapshot_hash(evidence_extraction):
    extraction = evidence_extraction or {}
    evidence_items = []
    for item in extraction.get('evidenceItems') or []:
        if not isinstance(item, dict):
            continue
        evidence_items.append({
            'evidenceId': item.get('evidenceId') or item.get('id'),
            'sourceType': item.get('sourceType'),
            'sourceRef': item.get('sourceRef'),
            'text': str(item.get('text') or item.get('summary') or '').strip(),
            'confidence': item.get('confidence'),
        })
    observations = []
    for item in extraction.get('observationEvidence') or []:
        if not isinstance(item, dict):
            continue
        observations.append({
            'observationCode': item.get('observationCode'),
            'evidenceLevel': item.get('evidenceLevel'),
            'performanceLevel': item.get('performanceLevel') or item.get('achievementLevel'),
            'evidenceIds': list(item.get('evidenceIds') or []),
            'suggestedBaseScore': item.get('suggestedBaseScore'),
            'suggestedScoreCap': item.get('suggestedScoreCap'),
        })
    quality = extraction.get('extractionQuality') or {}
    canonical = {
        'trackId': extraction.get('trackId'),
        'trackName': extraction.get('trackName'),
        'ruleVersion': extraction.get('ruleVersion'),
        'ruleHash': extraction.get('ruleHash'),
        'status': extraction.get('status'),
        'publicationEligible': quality.get('publicationEligible'),
        'transcriptCoverage': quality.get('transcriptCoverage'),
        'evidenceItems': evidence_items,
        'observationEvidence': observations,
        'deductionCandidates': [
            {
                'observationCode': item.get('observationCode'),
                'penaltyRuleCode': item.get('penaltyRuleCode') or item.get('deductionRuleCode'),
                'deductedPoints': item.get('deductedPoints') or item.get('points'),
                'triggerFact': item.get('triggerFact') or item.get('reason'),
                'evidenceIds': list(item.get('evidenceIds') or []),
            }
            for item in (extraction.get('deductionCandidates') or [])
            if isinstance(item, dict)
        ],
    }
    return _stable_hex(canonical)


def _stable_hex(value) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    ).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def _build_shadow_evidence_anchors(evidence_items):
    anchors = []
    ids_by_evidence_id = {}
    for item in evidence_items:
        if not isinstance(item, dict):
            continue
        evidence_id = item.get('evidenceId')
        text = str(item.get('text') or '').strip()
        source_ref = str(item.get('sourceRef') or '').strip()
        if not evidence_id or not text:
            continue
        anchor_id = len(anchors) + 1
        ids_by_evidence_id[str(evidence_id)] = anchor_id
        start_ms, end_ms = _source_ref_time_range_ms(source_ref)
        anchors.append({
            'id': anchor_id,
            'anchorType': item.get('sourceType') or 'evidence',
            'anchorTitle': item.get('title') or source_ref or f"证据 {anchor_id}",
            'evidenceText': text,
            'sourceRef': source_ref,
            'startMs': start_ms,
            'endMs': end_ms,
            'confidence': _safe_float(item.get('confidence')),
            'validityStatus': item.get('validityStatus') or 'valid',
        })
    return anchors, ids_by_evidence_id


def _enrich_evidence_anchors_with_score_links(
    evidence_anchors,
    *,
    observations,
    deductions,
    loss_ledger,
):
    """Attach real observation / loss links so the timeline can stop guessing."""
    if not evidence_anchors:
        return
    obs_by_anchor = {}
    dim_by_anchor = {}
    loss_by_anchor = {}
    risk_by_anchor = {}

    for observation in observations or []:
        if not isinstance(observation, dict):
            continue
        code = str(observation.get('observationCode') or '').strip()
        if not code:
            continue
        dimension = str(
            observation.get('dimensionName')
            or observation.get('dimensionCode')
            or ''
        ).strip()
        for anchor_id in observation.get('evidenceAnchorIds') or []:
            key = str(anchor_id)
            obs_by_anchor.setdefault(key, [])
            if code not in obs_by_anchor[key]:
                obs_by_anchor[key].append(code)
            if dimension:
                dim_by_anchor.setdefault(key, [])
                if dimension not in dim_by_anchor[key]:
                    dim_by_anchor[key].append(dimension)
            # Low evidence or incomplete performance is a soft risk signal.
            if str(observation.get('evidenceLevel') or '') in {'E0', 'E1'}:
                risk_by_anchor[key] = max(risk_by_anchor.get(key, 'ok'), 'warning', key=_risk_rank)
            gap = float(observation.get('performanceGap') or 0) + float(
                observation.get('evidenceLimitedGap') or 0
            )
            if gap > 0:
                risk_by_anchor[key] = max(risk_by_anchor.get(key, 'ok'), 'warning', key=_risk_rank)

    for deduction in deductions or []:
        if not isinstance(deduction, dict):
            continue
        if str(deduction.get('scoreEffect') or '') != 'subtractive':
            continue
        for anchor_id in deduction.get('evidenceAnchorIds') or []:
            risk_by_anchor[str(anchor_id)] = 'danger'

    for loss in loss_ledger or []:
        if not isinstance(loss, dict):
            continue
        points = float(loss.get('points') or 0)
        if points <= 0:
            continue
        cause = str(loss.get('causeCode') or loss.get('lossType') or '').strip()
        for anchor_id in loss.get('evidenceAnchorIds') or []:
            key = str(anchor_id)
            loss_by_anchor.setdefault(key, [])
            if cause and cause not in loss_by_anchor[key]:
                loss_by_anchor[key].append(cause)
            tone = 'danger' if str(loss.get('lossType') or '') == 'hard_violation' else 'warning'
            risk_by_anchor[key] = max(risk_by_anchor.get(key, 'ok'), tone, key=_risk_rank)

    for anchor in evidence_anchors:
        if not isinstance(anchor, dict):
            continue
        key = str(anchor.get('id') or '')
        codes = obs_by_anchor.get(key) or []
        dims = dim_by_anchor.get(key) or []
        losses = loss_by_anchor.get(key) or []
        if codes:
            anchor['observationCodes'] = codes
        if dims:
            anchor['dimensionNames'] = dims
            anchor['dimension'] = dims[0]
        if losses:
            anchor['linkedLossCauses'] = losses
        if risk_by_anchor.get(key):
            anchor['riskTone'] = risk_by_anchor[key]
        anchor['scoreLinked'] = bool(codes or losses)


def _risk_rank(value: str) -> int:
    order = {'ok': 0, 'warning': 1, 'danger': 2}
    return order.get(str(value or 'ok'), 0)


def _source_ref_time_range_ms(source_ref: str) -> tuple[int | None, int | None]:
    match = re.search(r'@(\d{1,2}):(\d{2})(?::(\d{2}))?', source_ref or '')
    if not match:
        return None, None
    parts = [int(value) if value is not None else None for value in match.groups()]
    if parts[2] is None:
        seconds = parts[0] * 60 + parts[1]
    else:
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
    start_ms = seconds * 1000
    return start_ms, start_ms + 30000


def _build_shadow_observations(observation_evidence, observation_rules, evidence_anchor_ids):
    observations = []
    for item in observation_evidence:
        if not isinstance(item, dict):
            continue
        observation_code = item.get('observationCode')
        rule = observation_rules.get(observation_code) or {}
        max_score = _safe_float(rule.get('maxScore') or item.get('maxScore'))
        # extraction 归一化后 suggestedScoreCap 为绝对分（scoreCapUnit=points）；
        # 手工/测试仍可传 0~1 比例帽。
        if str(item.get('scoreCapUnit') or '').lower() == 'points':
            score_cap = round(min(max_score, max(0.0, _safe_float(item.get('suggestedScoreCap')))), 2) if max_score > 0 else _safe_float(item.get('suggestedScoreCap'))
        else:
            score_cap = _normalized_score_cap(item.get('suggestedScoreCap'), max_score)
        base_score = _safe_float(
            _first_present(item.get('suggestedBaseScore'), item.get('baseScore'), score_cap)
        )
        # 二次兜底：E0 缺证非红线时 base 不低于 scoreCap（与 extraction 地板一致）
        evidence_level = str(item.get('evidenceLevel') or 'E0').upper()
        validity = str(item.get('validityStatus') or '')
        perf_status = str(item.get('performanceAssessmentStatus') or '')
        if (
            evidence_level == 'E0'
            and score_cap > 0
            and base_score < score_cap
            and perf_status != 'hard_redline_zero'
            and 'redline' not in validity.lower()
        ):
            base_score = score_cap
        evidence_ids = item.get('evidenceIds') or []
        observations.append({
            'observationCode': observation_code,
            'observationName': item.get('observationName') or rule.get('observationName'),
            'dimensionCode': item.get('dimensionCode') or rule.get('dimensionCode'),
            'dimensionName': item.get('dimensionName') or rule.get('dimensionName'),
            'maxScore': max_score,
            'baseScore': base_score,
            'rawScore': base_score,
            'scoreCap': score_cap,
            'evidenceLevel': evidence_level,
            'confidence': item.get('confidence') or 0,
            'validityStatus': item.get('validityStatus') or 'valid',
            'modelReason': item.get('supportSummary') or item.get('achievementReason') or '',
            'performanceReason': item.get('performanceReason') or item.get('achievementReason') or '',
            'evidenceReason': item.get('evidenceReason') or item.get('supportSummary') or '',
            'performanceAssessmentStatus': item.get('performanceAssessmentStatus') or '',
            'evidenceAnchorIds': _anchor_ids_for_evidence_ids(evidence_ids, evidence_anchor_ids),
            'trackDefinition': rule.get('trackDefinition'),
            'requiredInfo': list(rule.get('requiredInfo') or []),
            'acceptableEvidence': list(rule.get('acceptableEvidence') or []),
            'trainingTaskTemplate': rule.get('trainingTaskTemplate'),
        })
    return observations


def _build_shadow_deductions(deduction_candidates, observation_rules=None, recovery_candidates=None):
    observation_rules = observation_rules or {}
    recovery_by_observation = {
        str(item.get('observationCode')): item
        for item in (recovery_candidates or [])
        if isinstance(item, dict) and item.get('observationCode')
    }
    deductions = []
    for index, item in enumerate(deduction_candidates):
        if not isinstance(item, dict):
            continue
        observation_code = item.get('observationCode')
        rule = observation_rules.get(observation_code) or {}
        default_deduction_rule = _first_dict(rule.get('deductionRules'))
        default_recovery_rule = _first_dict(rule.get('recoveryRules'))
        recovery_candidate = recovery_by_observation.get(str(observation_code)) or {}
        deduction_rule_code = _first_present(
            item.get('deductionRuleCode'),
            item.get('ruleCode'),
            default_deduction_rule.get('deductionId'),
            default_deduction_rule.get('ruleCode'),
            default_deduction_rule.get('deductionRuleCode'),
            f"candidate-{index + 1}",
        )
        deduction_id = item.get('deductionId') or (
            deduction_rule_code
            if str(deduction_rule_code).startswith(f"{observation_code}-")
            or f"-{observation_code}-" in str(deduction_rule_code)
            else f"{observation_code}:{deduction_rule_code}"
        )
        deducted_points = _safe_float(
            _first_present(
                item.get('deductedPoints'),
                item.get('deductionScore'),
                item.get('points'),
                default_deduction_rule.get('deductionScore'),
                0,
            )
        )
        max_recoverable = _safe_float(
            _first_present(
                item.get('maxRecoverablePoints'),
                item.get('recoverableScore'),
                default_recovery_rule.get('recoverableScore'),
                deducted_points,
            ),
            deducted_points,
        )
        score_effect, penalty_type = _classify_deduction_effect(
            item,
            default_deduction_rule,
            deduction_rule_code,
        )
        deductions.append({
            'deductionId': deduction_id,
            'deductionRuleCode': deduction_rule_code,
            'penaltyRuleCode': _first_present(
                item.get('penaltyRuleCode'),
                default_deduction_rule.get('penaltyRuleCode'),
                deduction_rule_code if penalty_type == 'hard_violation' else None,
            ),
            'penaltyType': penalty_type,
            'scoreEffect': score_effect,
            'causeCode': _first_present(
                item.get('causeCode'),
                f"{observation_code}:{deduction_rule_code}",
            ),
            'triggerFact': _first_present(
                item.get('triggerFact'),
                item.get('eventFact'),
                default_deduction_rule.get('triggerFact'),
            ),
            'observationCode': observation_code,
            'dimensionCode': item.get('dimensionCode') or rule.get('dimensionCode'),
            'deductedPoints': deducted_points,
            'maxRecoverablePoints': min(max_recoverable, deducted_points),
            'reason': _first_present(
                item.get('reason'),
                item.get('ruleDescription'),
                default_deduction_rule.get('reason'),
                '证据不足',
            ),
            'requiredFix': _first_present(
                item.get('requiredFix'),
                recovery_candidate.get('suggestion'),
                recovery_candidate.get('condition'),
                default_recovery_rule.get('condition'),
                rule.get('trainingTaskTemplate'),
                '补齐可定位证据',
            ),
            'acceptanceCriteria': _first_present(
                item.get('acceptanceCriteria'),
                recovery_candidate.get('acceptanceCriteria'),
                _materials_acceptance(default_recovery_rule.get('acceptableMaterials')),
                '证据可定位且能支撑观测点',
            ),
            'evidenceLevel': item.get('evidenceLevel') or 'E0',
            'confidence': item.get('confidence') or 0,
            'status': item.get('status') or 'new',
            'evidenceIds': item.get('evidenceIds') or [],
            'evidenceAnchorIds': [],
        })
    return deductions


def _classify_deduction_effect(item, rule, rule_code):
    explicit_type = str(
        _first_present(
            item.get('penaltyType'),
            item.get('lossType'),
            rule.get('penaltyType'),
            rule.get('lossType'),
            '',
        )
    ).strip().lower().replace('-', '_')
    code = str(rule_code or '').strip().lower().replace('_', '-')

    if explicit_type in {'evidence_gap', 'evidence_limited'} or 'evidence-gap' in code:
        return 'diagnostic_only', 'evidence_gap'
    if explicit_type in {'performance_gap', 'achievement_gap'} or 'performance-gap' in code:
        return 'included_in_performance', 'performance_gap'
    if explicit_type != 'hard_violation':
        return 'diagnostic_only', explicit_type or 'unclassified_legacy'

    penalty_rule_code = _first_present(
        item.get('penaltyRuleCode'),
        rule.get('penaltyRuleCode'),
        rule_code,
    )
    trigger_fact = _first_present(
        item.get('triggerFact'),
        item.get('eventFact'),
        rule.get('triggerFact'),
    )
    evidence_ids = item.get('evidenceIds') or []
    if not penalty_rule_code or not trigger_fact or not evidence_ids:
        return 'diagnostic_only', 'invalid_hard_violation_candidate'
    return 'subtractive', 'hard_violation'


def _materials_acceptance(value):
    materials = [str(item).strip() for item in (value or []) if str(item).strip()]
    if not materials:
        return None
    return f"至少提供以下一类可核验材料：{' / '.join(materials[:5])}"


def _first_dict(value):
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return {}


def _first_present(*values):
    for value in values:
        if value is not None and value != '':
            return value
    return None


def _normalized_score_cap(value, max_score: float) -> float:
    cap = _safe_float(value)
    if max_score > 0 and 0 <= cap <= 1:
        return round(cap * max_score, 2)
    if max_score > 0:
        return round(min(cap, max_score), 2)
    return cap


def _anchor_ids_for_evidence_ids(evidence_ids, evidence_anchor_ids):
    anchor_ids = []
    for evidence_id in evidence_ids or []:
        anchor_id = evidence_anchor_ids.get(str(evidence_id))
        if anchor_id is not None and anchor_id not in anchor_ids:
            anchor_ids.append(anchor_id)
    return anchor_ids


def _without_llm_scores(value):
    """Drop any model-provided score fields before exposing evidence extraction."""
    blocked = {
        'overall_score', 'overallScore', 'dimension_scores', 'dimensionScores',
        'dimensions_score', 'dimensionsScore', 'final_score', 'finalScore',
        'score', 'total_score', 'totalScore',
    }
    if isinstance(value, list):
        return [_without_llm_scores(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _without_llm_scores(item)
            for key, item in value.items()
            if key not in blocked
        }
    return value


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return default
