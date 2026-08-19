package com.orep.backend.service;

import com.orep.backend.dto.SubstanceClaim;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class SubstanceClaimEvaluatorTest {

    @Test
    void alwaysReturnsExactlyThreeClaimTypes() {
        List<SubstanceClaim> claims = SubstanceClaimEvaluator.evaluate(new SubstanceClaimEvaluator.ClaimEvidence());
        assertEquals(3, claims.size());
        assertEquals("wrapper", claims.get(0).getClaimType());
        assertEquals("advancement", claims.get(1).getClaimType());
        assertEquals("value", claims.get(2).getClaimType());
        for (SubstanceClaim claim : claims) {
            assertEquals("unverified", claim.getClaimStatus());
            assertTrue(claim.getStatement().contains("本场未核验"));
            assertTrue(claim.getEvidenceRefs().isEmpty());
            assertTrue(claim.getSources().isEmpty());
        }
    }

    @Test
    void wrapperShellSampleCannotPass() {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.transcript = "我们基于开源项目改了改，很快就做完了。";
        evidence.observations = "口号包装，无运行画面，无代码仓库。";
        SubstanceClaim wrapper = byType(SubstanceClaimEvaluator.evaluate(evidence), "wrapper");
        assertNotEquals("pass", wrapper.getVerdict());
        assertEquals("fail", wrapper.getVerdict());
        assertEquals("unverified", wrapper.getClaimStatus());
        assertTrue(wrapper.getStatement().contains("本场未核验"));
        assertTrue(wrapper.getEvidenceRefs().isEmpty());
    }

    @Test
    void oralAdvancementCannotPass() {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.transcript = "我们的方案国际领先，技术非常先进。";
        evidence.observations = "仅口头先进，无对比、测试数或真实调用。";
        SubstanceClaim advancement = byType(SubstanceClaimEvaluator.evaluate(evidence), "advancement");
        assertNotEquals("pass", advancement.getVerdict());
        assertEquals("fail", advancement.getVerdict());
        assertTrue(advancement.getStatement().contains("本场未核验") || "seen_in_session".equals(advancement.getClaimStatus()));
    }

    @Test
    void retrievalOffNeverReturnsRetrievedCited() {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.retrievalEnabled = false;
        evidence.transcript = "对照 github.com/foo/bar 已验证领先。";
        evidence.observations = "提到公开仓库。";
        evidence.evidenceRefs.add("anchor-1");
        for (SubstanceClaim claim : SubstanceClaimEvaluator.evaluate(evidence)) {
            assertNotEquals("retrieved_cited", claim.getClaimStatus());
            assertTrue(claim.getSources() == null || claim.getSources().isEmpty());
        }
    }

    @Test
    void unverifiedStatementBansBoosterWords() {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.transcript = "我们赋能行业、填补空白、已经验证。";
        for (SubstanceClaim claim : SubstanceClaimEvaluator.evaluate(evidence)) {
            if ("unverified".equals(claim.getClaimStatus())) {
                assertTrue(claim.getStatement().contains("本场未核验"));
                assertFalse(claim.getStatement().contains("赋能"));
                assertFalse(claim.getStatement().contains("领先"));
                assertFalse(claim.getStatement().contains("填补空白"));
                assertFalse(claim.getStatement().contains("已验证"));
            }
        }
    }

    @Test
    void liveGreenhouseLikeSessionDoesNotPassAdvancementWithoutMetrics() {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.transcript = "琉璃新区智能大棚环境监测。现场演示了蓝牙连接、自动排风和AI问答。技术选型 MUSO AI、Ollama。";
        evidence.observations = "未提供具体技术指标、对比数据或性能测试结果。未展示IDE/仓库画面。用户为农户，解决人工成本痛点。";
        evidence.evidenceRefs.add("10");
        List<SubstanceClaim> claims = SubstanceClaimEvaluator.evaluate(evidence);
        assertNotEquals("pass", byType(claims, "wrapper").getVerdict());
        assertNotEquals("pass", byType(claims, "advancement").getVerdict());
        assertNotEquals("pass", byType(claims, "value").getVerdict());
        assertNotEquals("retrieved_cited", byType(claims, "value").getClaimStatus());
    }

    private static SubstanceClaim byType(List<SubstanceClaim> claims, String type) {
        return claims.stream().filter(claim -> type.equals(claim.getClaimType())).findFirst().orElseThrow();
    }
}
