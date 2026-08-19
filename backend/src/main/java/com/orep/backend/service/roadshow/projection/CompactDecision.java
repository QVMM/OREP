package com.orep.backend.service.roadshow.projection;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class CompactDecision {
    public Map<String, Object> selected;
    public final List<Map<String, Object>> runnerUp = new ArrayList<>();
    public final List<Map<String, Object>> eliminatedKey = new ArrayList<>();
    public final List<Map<String, Object>> reservedNext = new ArrayList<>();
    public final List<String> traceSteps = new ArrayList<>();
    public final List<String> reasons = new ArrayList<>();

    public Map<String, Object> toMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("selected", selected == null ? List.of() : List.of(selected));
        m.put("runner_up", List.copyOf(runnerUp.subList(0, Math.min(2, runnerUp.size()))));
        m.put("eliminated_key", List.copyOf(eliminatedKey.subList(0, Math.min(2, eliminatedKey.size()))));
        m.put("reserved_next", List.copyOf(reservedNext.subList(0, Math.min(1, reservedNext.size()))));
        m.put("trace_steps", List.copyOf(traceSteps));
        m.put("reasons", List.copyOf(reasons.subList(0, Math.min(4, reasons.size()))));
        return m;
    }
}
