package com.orep.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.TrackEvidenceSchema;
import com.orep.backend.mapper.TrackEvidenceSchemaMapper;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.List;

@Service
public class TrackEvidenceSchemaService {
    private static final String STATUS_ACTIVE = "active";
    private static final String ACTIVE_SLOT = "ACTIVE";
    private static final String SCHEMA_VERSION = "v1.2";
    private static final String HASH_FIELD_SEPARATOR = "\u001F";

    private final TrackEvidenceSchemaMapper mapper;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public TrackEvidenceSchemaService(TrackEvidenceSchemaMapper mapper) {
        this.mapper = mapper;
    }

    public TrackEvidenceSchema resolveActive(String trackId, String trackName) {
        LambdaQueryWrapper<TrackEvidenceSchema> wrapper = new LambdaQueryWrapper<TrackEvidenceSchema>()
                .eq(TrackEvidenceSchema::getStatus, STATUS_ACTIVE)
                .eq(TrackEvidenceSchema::getActiveSlot, ACTIVE_SLOT)
                .last("LIMIT 1");

        if (trackId != null && !trackId.isBlank()) {
            wrapper.eq(TrackEvidenceSchema::getTrackId, trackId);
        } else if (trackName != null && !trackName.isBlank()) {
            wrapper.eq(TrackEvidenceSchema::getTrackName, trackName);
        } else {
            throw new IllegalArgumentException("trackId 或 trackName 不能为空");
        }

        TrackEvidenceSchema active = mapper.selectOne(wrapper);
        if (active == null) {
            throw new IllegalStateException("未找到启用证据结构，请联系管理员");
        }
        return active;
    }

    public TrackEvidenceSchema sampleSchema(String trackName) {
        String normalizedName = trackName == null ? "" : trackName.trim();
        if ("新一代信息技术赛道".equals(normalizedName)) {
            return build(
                    "track-it",
                    "新一代信息技术赛道",
                    List.of("技术架构图", "代码仓库", "系统演示视频", "数据与实验记录", "现场演示稳定性记录"),
                    List.of("代码/系统演示", "技术架构", "数据与实验", "现场演示稳定性"),
                    List.of("运行核心业务流程", "展示关键代码与模块映射", "复现实验数据结论", "现场演示稳定性验证"),
                    List.of("模板套壳", "第三方系统二次包装", "低代码平台替代核心实现", "演示功能找不到代码对应"),
                    List.of("公开模板结构高度相似", "比赛前一次性导入大量代码", "账号或域名指向第三方 SaaS"),
                    List.of("代码与演示功能可对应", "架构说明能解释核心实现", "数据与实验记录可复核", "现场演示稳定性达到核心流程连续完成"));
        }
        if ("医学技术赛道".equals(normalizedName)) {
            return build(
                    "track-medical-technology",
                    "医学技术赛道",
                    List.of("临床/适用场景说明", "伦理合规材料", "实验验证记录", "安全风险清单", "转化路径计划"),
                    List.of("临床/适用场景", "伦理合规", "实验验证", "安全风险", "转化路径"),
                    List.of("说明适用边界", "展示实验或质控流程", "复核风险控制步骤", "解释转化路径里程碑"),
                    List.of("缺少伦理合规说明", "实验验证无法复核", "夸大临床效果", "安全风险未闭环"),
                    List.of("机构能力被包装成团队项目", "设备自动输出被包装成学生能力", "临床背书替代项目证据"),
                    List.of("临床/适用场景边界清晰", "伦理合规材料完整", "实验验证可追溯", "安全风险有控制方案", "转化路径可执行"));
        }
        if ("餐饮赛道".equals(normalizedName)) {
            return build(
                    "track-catering",
                    "餐饮赛道",
                    List.of("产品制作流程记录", "食品安全台账", "成本毛利表", "服务运营记录", "现场出品一致性记录"),
                    List.of("产品制作流程", "食品安全", "成本毛利", "服务运营", "现场出品一致性"),
                    List.of("现场完成关键制作步骤", "展示温控留样记录", "核算单品成本毛利", "说明服务运营排班与动线"),
                    List.of("预制成品冒充现场制作", "食品安全记录后补", "成本毛利无法对应", "现场出品一致性不足"),
                    List.of("外购成品包装", "文化故事替代制作技能", "加盟供应链能力被包装成团队能力"),
                    List.of("产品制作流程可现场复现", "食品安全记录完整", "成本毛利测算可核验", "服务运营有过程证据", "现场出品一致性稳定"));
        }
        if ("商贸赛道".equals(normalizedName)) {
            return build(
                    "track-ed3d87701522",
                    "商贸赛道",
                    List.of("商业模式说明", "交易流程记录", "客户调研与订单证据", "供应链与库存记录", "成本收益测算表", "营销运营数据"),
                    List.of("商品/服务展示", "交易流程", "客户需求验证", "供应链履约", "成本收益", "营销运营"),
                    List.of("演示从获客到下单的完整流程", "展示客户需求或订单证据", "核算单品/单客成本收益", "说明供应链履约与库存周转", "复盘营销转化数据"),
                    List.of("只讲商业故事但缺少交易证据", "订单或客户数据无法核验", "成本收益测算口径不清", "供应链履约风险未说明", "把第三方平台能力包装为团队经营能力"),
                    List.of("套用电商模板无真实商品/服务闭环", "用平台后台截图替代自有经营数据", "供应商能力被包装成团队能力", "虚构订单或客户访谈", "只展示宣传页不展示交易过程"),
                    List.of("商业模式与交易流程闭环清晰", "客户需求和订单证据可核验", "成本收益测算口径一致", "供应链履约过程可追溯", "营销运营数据能支撑结论"));
        }
        throw new IllegalArgumentException("仅支持新一代信息技术赛道、医学技术赛道、餐饮赛道、商贸赛道样板");
    }

    public TrackEvidenceSchema generatedSchema(String trackId, String trackName) {
        String normalizedName = trackName == null ? "" : trackName.trim();
        if (normalizedName.isBlank()) {
            normalizedName = "未指定赛道";
        }
        String normalizedId = trackId == null ? "" : trackId.trim();
        if (normalizedId.isBlank()) {
            normalizedId = "track-generated-" + sha256(normalizedName).substring(0, 12);
        }

        return build(
                normalizedId,
                normalizedName,
                List.of(
                        normalizedName + "项目方案/PPT",
                        normalizedName + "现场演示视频",
                        normalizedName + "过程记录与佐证材料",
                        normalizedName + "数据、成本或实验记录",
                        normalizedName + "团队分工与答辩记录"),
                List.of(
                        "项目目标与赛道匹配",
                        "核心技能操作过程",
                        "成果展示与应用场景",
                        "数据支撑与可验证性",
                        "现场表达与团队协作"),
                List.of(
                        "展示项目核心流程",
                        "说明赛道相关技能方法",
                        "复核数据或过程证据",
                        "解释应用价值与风险控制",
                        "完成团队分工答辩"),
                List.of(
                        "关键证据缺失",
                        "过程记录无法复核",
                        "成果与赛道能力不匹配",
                        "第三方能力被包装为团队能力",
                        "应用价值或风险说明不足"),
                List.of(
                        "模板化材料替代真实过程",
                        "外部平台能力替代团队实现",
                        "供应商或机构能力被包装成项目能力",
                        "演示结果无法对应过程证据"),
                List.of(
                        "赛道目标与项目内容一致",
                        "核心过程证据可追溯",
                        "现场演示能支撑评分项",
                        "数据和材料口径一致",
                        "风险说明与改进路径清晰"));
    }

    private TrackEvidenceSchema build(String trackId,
                                      String trackName,
                                      List<String> materialTypes,
                                      List<String> frameTargets,
                                      List<String> demoActions,
                                      List<String> riskPatterns,
                                      List<String> thirdPartySignals,
                                      List<String> acceptableEvidenceLevels) {
        TrackEvidenceSchema schema = new TrackEvidenceSchema();
        schema.setTrackId(trackId);
        schema.setTrackName(trackName);
        schema.setSchemaVersion(SCHEMA_VERSION);
        schema.setMaterialTypesJson(jsonArray(materialTypes));
        schema.setFrameTargetsJson(jsonArray(frameTargets));
        schema.setDemoActionsJson(jsonArray(demoActions));
        schema.setRiskPatternsJson(jsonArray(riskPatterns));
        schema.setThirdPartyPackagingSignalsJson(jsonArray(thirdPartySignals));
        schema.setAcceptableEvidenceLevelsJson(jsonArray(acceptableEvidenceLevels));
        schema.setSchemaHash(calculateSchemaHash(schema));
        schema.setStatus(STATUS_ACTIVE);
        schema.setActiveSlot(ACTIVE_SLOT);
        return schema;
    }

    String calculateSchemaHash(TrackEvidenceSchema schema) {
        return sha256(String.join(HASH_FIELD_SEPARATOR,
                nonNull(schema.getTrackId()),
                nonNull(schema.getTrackName()),
                nonNull(schema.getSchemaVersion()),
                nonNull(schema.getMaterialTypesJson()),
                nonNull(schema.getFrameTargetsJson()),
                nonNull(schema.getDemoActionsJson()),
                nonNull(schema.getRiskPatternsJson()),
                nonNull(schema.getThirdPartyPackagingSignalsJson()),
                nonNull(schema.getAcceptableEvidenceLevelsJson())));
    }

    private String jsonArray(List<String> values) {
        try {
            return objectMapper.writeValueAsString(values);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("schema JSON 生成失败", e);
        }
    }

    private String nonNull(String value) {
        return value == null ? "" : value;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("schema hash 生成失败", e);
        }
    }
}
