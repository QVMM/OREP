package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class DocketTaskBookTest {

    @Test
    void reportSnapshotWinsOverDocket() {
        DocketTaskBook.Snapshot snapshot = DocketTaskBook.resolve(
                true, "{\"items\":[{\"title\":\"本场\"}]}",
                true, "{\"items\":[{\"title\":\"卷宗\"}]}"
        );
        assertTrue(snapshot.published());
        assertTrue(snapshot.json().contains("本场"));
    }

    @Test
    void laterRunReadsDocketWhenOwnReportUnpublished() {
        DocketTaskBook.Snapshot snapshot = DocketTaskBook.resolve(
                false, null,
                true, "{\"items\":[{\"title\":\"补齐差异与仓库证据\"}]}"
        );
        assertTrue(snapshot.published());
        assertTrue(snapshot.json().contains("补齐差异"));
    }

    @Test
    void unpublishedEverywhereStaysDraft() {
        DocketTaskBook.Snapshot snapshot = DocketTaskBook.resolve(false, "{}", null, null);
        assertFalse(snapshot.published());
        assertEquals(DocketTaskBook.Snapshot.unpublished(), snapshot);
        assertFalse(DocketTaskBook.flag(0, false));
        assertTrue(DocketTaskBook.flag(0, 1));
    }

    @Test
    void bookPublishedByThisSessionIsNotPrior() {
        DocketTaskBook.Snapshot prior = DocketTaskBook.prior(
                false, null,
                true, "{\"items\":[{\"title\":\"补齐差异与仓库证据\"}]}",
                47L, 47L
        );
        assertFalse(prior.published());
        assertEquals(DocketTaskBook.Snapshot.unpublished(), prior);
    }

    @Test
    void bookPublishedOnEarlierRunIsPrior() {
        DocketTaskBook.Snapshot prior = DocketTaskBook.prior(
                false, null,
                true, "{\"items\":[{\"title\":\"补齐差异与仓库证据\"}]}",
                45L, 47L
        );
        assertTrue(prior.published());
        assertTrue(prior.json().contains("补齐差异"));
    }

    @Test
    void newDocketReadsTeamTrackBookAsPrior() {
        DocketTaskBook.Snapshot prior = DocketTaskBook.priorAcross(
                DocketTaskBook.Snapshot.unpublished(),
                false,
                new DocketTaskBook.Snapshot(true, "{\"items\":[{\"title\":\"补齐差异与仓库证据\"}]}", 52L),
                53L
        );
        assertTrue(prior.published());
        assertTrue(prior.json().contains("补齐差异"));
    }

    @Test
    void thisRoundBookBlocksOlderDocketFallback() {
        DocketTaskBook.Snapshot prior = DocketTaskBook.priorAcross(
                DocketTaskBook.Snapshot.unpublished(),
                true,
                new DocketTaskBook.Snapshot(true, "{\"items\":[{\"title\":\"旧卷宗书\"}]}", 47L),
                52L
        );
        assertFalse(prior.published());
    }

    @Test
    void sameDocketPriorWinsOverTeamTrack() {
        DocketTaskBook.Snapshot prior = DocketTaskBook.priorAcross(
                new DocketTaskBook.Snapshot(true, "{\"items\":[{\"title\":\"本卷宗上场\"}]}", 51L),
                false,
                new DocketTaskBook.Snapshot(true, "{\"items\":[{\"title\":\"他卷宗\"}]}", 47L),
                53L
        );
        assertTrue(prior.json().contains("本卷宗上场"));
    }

    @Test
    void bookPublishedOnLaterRunIsNotPriorForOlderSession() {
        DocketTaskBook.Snapshot prior = DocketTaskBook.prior(
                false, null,
                true, "{\"items\":[{\"title\":\"补齐差异与仓库证据\"}]}",
                47L, 45L
        );
        assertFalse(prior.published());
    }
}
