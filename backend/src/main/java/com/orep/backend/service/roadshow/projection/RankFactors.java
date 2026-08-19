package com.orep.backend.service.roadshow.projection;

public record RankFactors(
        int impact,
        int ostensible,
        int bridgeValue,
        String cluster,
        int freshness,
        boolean expired,
        boolean irrelevant,
        boolean tech
) {
    public static RankFactors of(int impact, int ostensible, int bridgeValue, String cluster, int freshness) {
        return new RankFactors(impact, ostensible, bridgeValue, cluster, freshness, false, false, false);
    }
}
