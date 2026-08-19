"""
能力画像服务
用 LLM 根据音视频融合数据生成选手能力画像和团队分工推断
画像是独立模块，与五维评分并列，互相印证但各自独立
"""
import os
import json
import logging
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class CharacterProfileService:
    """能力画像生成"""

    def __init__(self):
        # 优先用 DashScope（兼容 OpenAI 接口），也支持 DeepSeek 直连
        self.dashscope_client = None
        self.deepseek_client = None

    def _dashscope_client(self) -> OpenAI:
        if not settings.DASHSCOPE_API_KEY:
            raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法生成能力画像")
        if self.dashscope_client is None:
            self.dashscope_client = OpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        return self.dashscope_client

    def _deepseek_client(self) -> OpenAI:
        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置，无法生成能力画像")
        if self.deepseek_client is None:
            self.deepseek_client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com"
            )
        return self.deepseek_client

    def _prepare_fusion_summary(self, fused_timeline: list[dict]) -> list[dict]:
        """精简时间序列数据用于 LLM prompt"""
        return [
            {
                "time": f"{f['time_min']}min",
                "visual": {
                    "gesture": f['gesture_score'],
                    "posture": f['posture_score'],
                    "expression": f['expression_score'],
                    "eye": f"{f['eye_direction']}({f['eye_score']})",
                    "impression": f['visual_impression'][:60]
                },
                "audio": {
                    "wpm": f['speech_rate'],
                    "pauses": f['pause_count'],
                    "fillers": f['filler_count'],
                    "text": f['text_preview'][:80]
                },
                "fusion": f['fusion_score']
            }
            for f in fused_timeline
        ]

    def _prepare_asr_samples(self, asr_segments: list[dict], max_samples: int = 30) -> str:
        """采样 ASR 片段用于 LLM 分析"""
        step = max(1, len(asr_segments) // max_samples)
        samples = []
        for seg in asr_segments[::step]:
            samples.append(f"[{seg['start']:.0f}-{seg['end']:.0f}s] {seg['text'][:120]}")
        return "\n".join(samples)

    def _build_prompt(
        self,
        fusion_summary: list[dict],
        asr_samples: str,
        trends: dict,
        contradictions: list[dict],
        project_info: dict,
        five_dim_scores: dict
    ) -> str:
        """构建画像生成 prompt"""

        project_name = project_info.get("project_name", "未命名")
        track = project_info.get("track", "未指定")
        team_size = project_info.get("team_size", 4)

        # 趋势图
        trend_lines = []
        for dim, data in trends.items():
            trend_lines.append(f"  {dim}: {data.get('sparkline', '')} (min={data.get('min')}, max={data.get('max')}, avg={data.get('avg')})")
        trend_text = "\n".join(trend_lines)

        # 矛盾点
        contra_text = "\n".join(
            f"  [{c['time_min']}min] {c['description']}"
            for c in contradictions[:10]
        ) if contradictions else "  无明显矛盾点"

        # 五维评分（引用）
        dim_text = ""
        if five_dim_scores:
            dims = five_dim_scores.get("dimensions", {})
            dim_lines = [f"  {v.get('name', k)}: {v.get('score', 0)}/{v.get('max_score', 100)}" for k, v in dims.items()]
            dim_text = "\n".join(dim_lines)

        return f"""你是一位专业的路演评估分析师。以下是一场职业技能大赛路演的音视频融合分析数据。

## 项目信息
- 项目名称：{project_name}
- 赛道：{track}
- 团队人数：{team_size}人

## 时间序列融合数据（每2分钟一个窗口）
{json.dumps(fusion_summary, ensure_ascii=False, indent=2)}

## 趋势图
{trend_text}

## 音视频矛盾点
{contra_text}

## 五维评分结果（供引用佐证）
{dim_text}

## ASR 转录关键片段
{asr_samples}

---

请生成一份**选手团队能力画像报告**。这是独立于五维评分的定性分析报告，需包含以下部分：

## 1. 路演整体节奏分析
分析全程表现变化的节奏特征，是否有"热身期""高峰期""疲劳期"。用具体时间点和数据支撑。

## 2. 团队分工推断（详细版）
根据转录内容、视觉变化、表现数据，推断每位选手：
- **选手编号**：A/B/C/D
- **负责时间段**：具体起止时间
- **角色定位**：项目经理/开发工程师/测试/演示等（从转录内容推断）
- **个人表现特征**：
  - 语速特点（偏快/稳定/偏慢，具体wpm范围）
  - 肢体风格（活跃/稳重/拘谨）
  - 表情特征（自信/紧张/平淡）
  - 眼神习惯（看观众/看屏幕/交替）
  - 专业领域（从转录内容推断他负责的技术方向）
- **个人强项**：该选手最突出的能力
- **个人弱项**：该选手需要提升的方面
- **个人改进建议**：针对性的建议

## 3. 视觉表现画像
根据肢体语言、表情、眼神数据，刻画团队的"上镜感"。不要泛泛而谈，要用数据说话。

## 4. 语音表达画像
根据语速、停顿、填充词数据，刻画团队的"口才感"。指出具体的好坏时刻。

## 5. 音视频关联洞察
- 哪些时刻视觉和音频表现一致（说明什么）？
- 哪些时刻有矛盾（矛盾的原因可能是什么）？
- 这种关联对评估有什么启示？

## 6. 个人能力画像（描述性，不打分）
对团队整体（或推断出的每位选手）进行描述：
- **表达力**：语速控制能力、语言流畅度、感染力、肢体语言配合度
- **逻辑力**：内容结构完整性、论证链条连贯度、板块衔接自然度
- **技术深度**：技术讲解的专业程度、对核心算法/架构的理解深度
- **应变力**：面对复杂内容时的节奏调整、卡顿时的恢复能力
- **团队协作**：分工清晰度、交接话术自然度、配合默契度

每个维度必须引用具体的时间点和数据作为证据。

## 7. 关键洞察（3-5条）
最重要的发现，每条要有具体证据（时间点+数据）。

## 8. 改进建议（针对性、可操作）
不能是"提升表达力"这种泛泛的建议，要具体到哪个时间段、哪个选手、做什么改进。禁止涉及"音视频同步"相关内容。

---

**注意**：
- 画像是定性的、描述性的，不要给分数（分数在五维评分里）
- 画像要引用五维评分的数据作为佐证
- 五维评分要通过画像的描述获得定性的解读
- 两者互相印证，但各自独立

用中文，Markdown格式。"""

    def _call_llm(self, prompt: str, provider: str = "dashscope") -> str:
        """调用 LLM 生成画像"""
        if provider == "dashscope":
            response = self._dashscope_client().chat.completions.create(
                model="qwen3.5-plus",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=6000,
            )
        elif provider == "deepseek":
            response = self._deepseek_client().chat.completions.create(
                model=settings.DEEPSEEK_MODEL or "deepseek-v4-pro",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=6000,
            )
        else:
            raise ValueError(f"不支持的 provider: {provider}")

        return response.choices[0].message.content

    def generate_profile(
        self,
        fused_timeline: list[dict],
        asr_segments: list[dict],
        trends: dict,
        contradictions: list[dict],
        project_info: dict,
        five_dim_scores: dict = None,
        provider: str = "dashscope"
    ) -> dict:
        """
        生成能力画像
        返回: { profile_markdown, provider, key_sections }
        """
        logger.info(f"开始生成能力画像 (provider={provider})")

        fusion_summary = self._prepare_fusion_summary(fused_timeline)
        asr_samples = self._prepare_asr_samples(asr_segments)

        prompt = self._build_prompt(
            fusion_summary, asr_samples, trends,
            contradictions, project_info,
            five_dim_scores or {}
        )

        try:
            profile_text = self._call_llm(prompt, provider)
        except Exception as e:
            logger.warning(f"{provider} 调用失败，尝试备用: {e}")
            fallback = "deepseek" if provider == "dashscope" else "dashscope"
            profile_text = self._call_llm(prompt, fallback)
            provider = fallback

        # 提取关键段落标记
        sections = self._extract_sections(profile_text)

        return {
            "profile_markdown": profile_text,
            "provider": provider,
            "sections": sections,
        }

    def _extract_sections(self, markdown: str) -> dict:
        """从 Markdown 中提取各段落标题"""
        sections = {}
        current = None
        for line in markdown.split("\n"):
            if line.startswith("## "):
                current = line.replace("## ", "").strip()
                sections[current] = ""
            elif current:
                sections[current] = (sections.get(current, "") + "\n" + line).strip()
        return sections


character_profile_service = CharacterProfileService()
