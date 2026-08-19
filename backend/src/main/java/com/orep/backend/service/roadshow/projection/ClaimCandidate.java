package com.orep.backend.service.roadshow.projection;

import java.util.LinkedHashSet;
import java.util.Set;

public final class ClaimCandidate {
    private final String stableId;
    private final String proposition;
    private final String extractedFact;
    private final String status;
    private final boolean evidenceVerified;
    private final RankFactors factors;
    private int chi;
    private final Set<String> contradictIds = new LinkedHashSet<>();
    private final Set<String> bridgesTo = new LinkedHashSet<>();

    public ClaimCandidate(
            String stableId,
            String proposition,
            String extractedFact,
            String status,
            boolean evidenceVerified,
            RankFactors factors,
            int chi
    ) {
        this.stableId = stableId;
        this.proposition = proposition;
        this.extractedFact = extractedFact;
        this.status = status;
        this.evidenceVerified = evidenceVerified;
        this.factors = factors;
        this.chi = chi;
    }

    public String stableId() { return stableId; }
    public String proposition() { return proposition; }
    public String extractedFact() { return extractedFact; }
    public String status() { return status; }
    public boolean evidenceVerified() { return evidenceVerified; }
    public RankFactors factors() { return factors; }
    public int chi() { return chi; }
    public void setChi(int chi) { this.chi = chi; }
    public Set<String> contradictIds() { return contradictIds; }
    public Set<String> bridgesTo() { return bridgesTo; }

    public ClaimCandidate withBridge(String toStableId) {
        bridgesTo.add(toStableId);
        return this;
    }

    public ClaimCandidate withContradict(String otherStableId) {
        contradictIds.add(otherStableId);
        return this;
    }
}
