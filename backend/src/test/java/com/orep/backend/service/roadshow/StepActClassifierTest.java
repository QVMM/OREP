package com.orep.backend.service.roadshow;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class StepActClassifierTest {

    @Test
    void problemFromLossAndPain() {
        assertEquals("problem", StepActClassifier.classify("平均损耗 23%，这是我们最大的痛点", "痛点"));
    }

    @Test
    void logisticsHandoffHasNoPage() {
        assertEquals("logistics", StepActClassifier.classify("接下来交给下一位同学，请回工位", ""));
    }

    @Test
    void demoFromLiveAction() {
        assertEquals("demo", StepActClassifier.classify("现在运行程序，拔掉土壤传感器通信线", ""));
    }

    @Test
    void methodFromArchitecture() {
        assertEquals("method", StepActClassifier.classify("系统自下而上分为五层，感知层到应用层", "架构"));
    }
}
