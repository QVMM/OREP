package com.orep.backend.service;

import com.orep.backend.dto.DocketIdentity;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class DocketIdServiceTest {

    private final DocketIdService service = new DocketIdService();

    @Test
    void sameIdentityCreatesSameDocketId() {
        String first = service.docketId(base());
        String second = service.docketId(base());
        assertEquals(first, second);
        assertEquals(64, first.length());
        assertTrue(first.matches("[0-9a-f]{64}"));
    }

    @Test
    void videoHashChangeCreatesDifferentDocket() {
        DocketIdentity other = base();
        other.setVideoSha256("bb".repeat(32));
        assertNotEquals(service.docketId(base()), service.docketId(other));
    }

    @Test
    void ruleHashChangeCreatesDifferentDocket() {
        DocketIdentity other = base();
        other.setRuleHash("cc".repeat(32));
        assertNotEquals(service.docketId(base()), service.docketId(other));
    }

    @Test
    void contractOrTrackChangeCreatesDifferentDocket() {
        DocketIdentity contract = base();
        contract.setContractVersion("ai-score-report-v4");
        DocketIdentity track = base();
        track.setTrackId("track-other");
        assertNotEquals(service.docketId(base()), service.docketId(contract));
        assertNotEquals(service.docketId(base()), service.docketId(track));
    }

    @Test
    void normalizesCaseAndTrim() {
        DocketIdentity dirty = base();
        dirty.setVideoSha256("  " + "AA".repeat(32) + "  ");
        dirty.setRuleHash("  " + "DD".repeat(32).toUpperCase() + "  ");
        DocketIdentity clean = base();
        clean.setVideoSha256("aa".repeat(32));
        clean.setRuleHash("dd".repeat(32));
        assertEquals(service.docketId(clean), service.docketId(dirty));
    }

    @Test
    void rejectsMissingFields() {
        DocketIdentity missingVideo = base();
        missingVideo.setVideoSha256("  ");
        assertThrows(IllegalArgumentException.class, () -> service.docketId(missingVideo));
        assertThrows(IllegalArgumentException.class, () -> service.docketId(null));
    }

    @Test
    void rejectsBlankRuleVersionRuleHashContractAndTrack() {
        DocketIdentity missingRuleVersion = base();
        missingRuleVersion.setRuleVersion("  ");
        assertThrows(IllegalArgumentException.class, () -> service.docketId(missingRuleVersion));

        DocketIdentity missingRuleHash = base();
        missingRuleHash.setRuleHash(null);
        assertThrows(IllegalArgumentException.class, () -> service.docketId(missingRuleHash));

        DocketIdentity missingContract = base();
        missingContract.setContractVersion("");
        assertThrows(IllegalArgumentException.class, () -> service.docketId(missingContract));

        DocketIdentity missingTrack = base();
        missingTrack.setTrackId(" \t");
        assertThrows(IllegalArgumentException.class, () -> service.docketId(missingTrack));
    }

    @Test
    void ruleVersionChangeCreatesDifferentDocket() {
        DocketIdentity other = base();
        other.setRuleVersion("v1.3");
        assertNotEquals(service.docketId(base()), service.docketId(other));
    }

    private DocketIdentity base() {
        DocketIdentity identity = new DocketIdentity();
        identity.setVideoSha256("aa".repeat(32));
        identity.setRuleVersion("v1.2");
        identity.setRuleHash("dd".repeat(32));
        identity.setContractVersion("ai-score-report-v3");
        identity.setTrackId("track-c889f0110e2d");
        return identity;
    }
}
