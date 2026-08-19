"""
音视频融合服务
将音频分析和视频分析按时间窗口对齐，计算融合评分，检测矛盾点
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class FusionService:
    """音视频数据融合"""

    # 融合权重
    AUDIO_WEIGHT = 0.6
    VISUAL_WEIGHT = 0.4

    # 填充词集合
    FILLER_WORDS = {
        "嗯", "啊", "那个", "这个", "就是说", "然后", "就是", "对吧",
        "对不对", "所以说", "反正", "其实", "基本上", "额", "呃", "嘛",
        "你看", "OK", "okay", "嗯嗯"
    }

    def compute_audio_window_features(
        self,
        asr_segments: list[dict],
        window_sec: int = 120
    ) -> list[dict]:
        """
        从 ASR 带时间戳的片段中，计算每个时间窗口的音频特征
        """
        by_window = {}
        for seg in asr_segments:
            wi = int(seg["start"] // window_sec)
            by_window.setdefault(wi, []).append(seg)

        features = []
        for wi in sorted(by_window.keys()):
            win_segs = by_window[wi]
            t_start = wi * window_sec
            t_end = (wi + 1) * window_sec

            full_text = " ".join(seg["text"].strip() for seg in win_segs)
            total_chars = len(full_text.replace(" ", ""))

            speak_dur = sum(seg["end"] - seg["start"] for seg in win_segs)
            wpm = total_chars / (speak_dur / 60) if speak_dur > 0 else 0

            # 停顿: 片段间隔 > 1.5s
            pauses = 0
            total_pause_dur = 0
            for i in range(1, len(win_segs)):
                gap = win_segs[i]["start"] - win_segs[i - 1]["end"]
                if gap > 1.5:
                    pauses += 1
                    total_pause_dur += gap

            # 填充词
            filler_count = 0
            filler_types = {}
            for fw in self.FILLER_WORDS:
                c = full_text.count(fw)
                if c > 0:
                    filler_count += c
                    filler_types[fw] = c

            # 评分（1-10）
            wpm_score = max(0, min(10, 10 - abs(wpm - 200) / 20))
            pause_score = max(0, 10 - pauses * 1.5)
            filler_score = max(0, 10 - filler_count * 0.5)

            features.append({
                "window_index": wi,
                "time_start_min": round(t_start / 60, 1),
                "time_end_min": round(t_end / 60, 1),
                "char_count": total_chars,
                "speak_duration_sec": round(speak_dur, 1),
                "speech_rate_wpm": round(wpm, 1),
                "speech_rate_score": round(wpm_score, 1),
                "pause_count": pauses,
                "pause_total_sec": round(total_pause_dur, 1),
                "pause_score": round(pause_score, 1),
                "filler_count": filler_count,
                "filler_types": filler_types,
                "filler_score": round(filler_score, 1),
                "audio_composite_score": round((wpm_score + pause_score + filler_score) / 3, 1),
                "text_preview": full_text[:100],
            })

        return features

    def fuse_time_series(
        self,
        video_per_frame: list[dict],
        audio_windows: list[dict],
        window_sec: int = 120
    ) -> list[dict]:
        """
        按时间窗口对齐音视频数据
        """
        fused = []

        for i, vframe in enumerate(video_per_frame):
            if "error" in vframe:
                continue

            ts_min = vframe.get("timestamp_min", i * window_sec / 60)

            # 找对应的音频窗口
            aw = None
            for a in audio_windows:
                if abs(a["time_start_min"] - ts_min) < 1:
                    aw = a
                    break

            # 视觉综合分
            gesture = vframe.get("gesture", {}).get("score", 0)
            posture = vframe.get("posture", {}).get("score", 0)
            expression = vframe.get("expression", {}).get("confidence", 0)
            eye = vframe.get("eye_contact", {}).get("score", 0)
            visual_composite = round((gesture + posture + expression + eye) / 4, 1)

            # 音频综合分
            audio_composite = aw["audio_composite_score"] if aw else 5.0

            # 融合分
            fusion_score = round(
                visual_composite * self.VISUAL_WEIGHT +
                audio_composite * self.AUDIO_WEIGHT,
                1
            )

            fused.append({
                "time_min": round(ts_min, 1),
                # 视觉维度
                "gesture_score": gesture,
                "gesture_desc": vframe.get("gesture", {}).get("desc", ""),
                "posture_score": posture,
                "posture_desc": vframe.get("posture", {}).get("desc", ""),
                "expression_score": expression,
                "expression_desc": vframe.get("expression", {}).get("desc", ""),
                "eye_direction": vframe.get("eye_contact", {}).get("direction", ""),
                "eye_score": eye,
                "scene_type": vframe.get("scene", {}).get("type", ""),
                "scene_has_screen": vframe.get("scene", {}).get("has_screen_share", False),
                "scene_people": vframe.get("scene", {}).get("people_count", 0),
                "active_speaker": vframe.get("active_speaker", {}),
                "visual_impression": vframe.get("impression", ""),
                # 音频维度
                "speech_rate": aw["speech_rate_wpm"] if aw else 0,
                "speech_rate_score": aw["speech_rate_score"] if aw else 0,
                "char_count": aw["char_count"] if aw else 0,
                "pause_count": aw["pause_count"] if aw else 0,
                "pause_score": aw["pause_score"] if aw else 0,
                "filler_count": aw["filler_count"] if aw else 0,
                "filler_score": aw["filler_score"] if aw else 0,
                "audio_score": audio_composite,
                "text_preview": aw["text_preview"] if aw else "",
                # 综合
                "visual_score": visual_composite,
                "fusion_score": fusion_score,
            })

        return fused

    def detect_contradictions(self, fused: list[dict], threshold: float = 2.0) -> list[dict]:
        """
        检测音视频矛盾点
        threshold: 视觉和音频分差超过此值认为矛盾
        """
        contradictions = []
        for f in fused:
            diff = abs(f["visual_score"] - f["audio_score"])
            if diff >= threshold:
                if f["visual_score"] > f["audio_score"]:
                    kind = "visual_good_audio_bad"
                    desc = f"视觉表现好({f['visual_score']})但语音表现差({f['audio_score']})"
                else:
                    kind = "audio_good_visual_bad"
                    desc = f"语音表现好({f['audio_score']})但视觉表现差({f['visual_score']})"

                contradictions.append({
                    "time_min": f["time_min"],
                    "kind": kind,
                    "description": desc,
                    "visual_score": f["visual_score"],
                    "audio_score": f["audio_score"],
                    "difference": round(diff, 1),
                })

        return contradictions

    def compute_trend_sparklines(self, fused: list[dict]) -> dict:
        """计算各维度的趋势数据（用于前端 sparkline 渲染）"""
        symbols = "▁▂▃▄▅▆▇█"

        def to_sparkline(values):
            if not values:
                return ""
            mn, mx = min(values), max(values)
            if mx == mn:
                return "▅" * len(values)
            return "".join(symbols[int((v - mn) / (mx - mn) * 7)] for v in values)

        def stats(values):
            if not values:
                return {"min": 0, "max": 0, "avg": 0}
            return {
                "min": min(values),
                "max": max(values),
                "avg": round(sum(values) / len(values), 1)
            }

        gestures = [f["gesture_score"] for f in fused]
        expressions = [f["expression_score"] for f in fused]
        eyes = [f["eye_score"] for f in fused]
        rates = [f["speech_rate"] for f in fused]
        pauses = [f["pause_count"] for f in fused]
        fusion_scores = [f["fusion_score"] for f in fused]

        return {
            "gesture": {"values": gestures, "sparkline": to_sparkline(gestures), **stats(gestures)},
            "expression": {"values": expressions, "sparkline": to_sparkline(expressions), **stats(expressions)},
            "eye_contact": {"values": eyes, "sparkline": to_sparkline(eyes), **stats(eyes)},
            "speech_rate": {"values": rates, "sparkline": to_sparkline(rates), **stats(rates)},
            "pauses": {"values": pauses, "sparkline": to_sparkline(pauses), **stats(pauses)},
            "fusion": {"values": fusion_scores, "sparkline": to_sparkline(fusion_scores), **stats(fusion_scores)},
        }

    def run_fusion(
        self,
        asr_segments: list[dict],
        video_per_frame: list[dict],
        window_sec: int = 120
    ) -> dict:
        """
        完整融合流水线
        返回: { timeline, contradictions, trends, summary }
        """
        logger.info(f"开始音视频融合: {len(video_per_frame)} 帧, 窗口={window_sec}s")

        # 1. 计算音频窗口特征
        audio_windows = self.compute_audio_window_features(asr_segments, window_sec)

        # 2. 时间对齐
        fused = self.fuse_time_series(video_per_frame, audio_windows, window_sec)

        # 3. 检测矛盾
        contradictions = self.detect_contradictions(fused)

        # 4. 趋势数据
        trends = self.compute_trend_sparklines(fused)

        # 5. 汇总
        fusion_scores = [f["fusion_score"] for f in fused]
        summary = {
            "total_windows": len(fused),
            "fusion_avg": round(sum(fusion_scores) / len(fusion_scores), 1) if fusion_scores else 0,
            "fusion_min": min(fusion_scores) if fusion_scores else 0,
            "fusion_max": max(fusion_scores) if fusion_scores else 0,
            "best_window": max(fused, key=lambda x: x["fusion_score"])["time_min"] if fused else 0,
            "worst_window": min(fused, key=lambda x: x["fusion_score"])["time_min"] if fused else 0,
            "contradiction_count": len(contradictions),
        }

        # 6. 屏幕内容汇总（从视频分析结果中提取，透传给评分服务）
        screen_content_summary = {}
        if video_per_frame:
            # 从 per_frame 数据中聚合 screen_content
            all_screen_types = {}
            all_content_types = {}
            all_visible_texts = []
            code_frames = []
            chart_frames = []
            standard_frames = []
            cost_frames = []
            security_frames = []
            collab_frames = []

            for i, vf in enumerate(video_per_frame):
                if "error" in vf:
                    continue
                sc = vf.get("screen_content", {})
                if not sc:
                    continue

                st = sc.get("screen_type", "无")
                all_screen_types[st] = all_screen_types.get(st, 0) + 1

                for ct in sc.get("content_types", []):
                    all_content_types[ct] = all_content_types.get(ct, 0) + 1

                vt = sc.get("visible_text_summary", "")
                if vt and vt != "无":
                    all_visible_texts.append({
                        "frame": vf.get("frame", i),
                        "timestamp_min": vf.get("timestamp_min", 0),
                        "text": vt
                    })

                # has_code 或屏幕类型/内容类型标明代码界面，均记入代码证据
                is_code_ui = bool(sc.get("has_code"))
                st_l = str(st or "")
                if "代码编辑" in st_l or st_l in ("IDE", "编辑器"):
                    is_code_ui = True
                if any(ct in ("代码展示", "代码", "源码") for ct in (sc.get("content_types") or [])):
                    is_code_ui = True
                if is_code_ui:
                    code_frames.append({
                        "frame": vf.get("frame", i),
                        "timestamp_min": vf.get("timestamp_min", 0),
                        "desc": vt or st_l or "代码相关画面",
                        "screen_type": st_l,
                    })

                if sc.get("has_data_chart"):
                    chart_frames.append({"frame": vf.get("frame", i), "timestamp_min": vf.get("timestamp_min", 0), "desc": sc.get("chart_desc", vt)})

                if "标准规范" in sc.get("content_types", []):
                    standard_frames.append({"frame": vf.get("frame", i), "timestamp_min": vf.get("timestamp_min", 0), "title": sc.get("ppt_title", ""), "text": vt})

                if "成本分析" in sc.get("content_types", []):
                    cost_frames.append({"frame": vf.get("frame", i), "timestamp_min": vf.get("timestamp_min", 0), "text": vt})

                if "安全方案" in sc.get("content_types", []):
                    security_frames.append({"frame": vf.get("frame", i), "timestamp_min": vf.get("timestamp_min", 0), "text": vt})

                tc = vf.get("team_collaboration", {})
                if tc.get("multi_person_visible"):
                    collab_frames.append({"frame": vf.get("frame", i), "timestamp_min": vf.get("timestamp_min", 0), "type": tc.get("collab_type", ""), "desc": tc.get("desc", "")})

            screen_content_summary = {
                "screen_type_distribution": all_screen_types,
                "content_type_counts": all_content_types,
                "visible_texts": all_visible_texts[:20],
                "code_detections": code_frames,
                "chart_detections": chart_frames,
                "standard_detections": standard_frames,
                "cost_detections": cost_frames,
                "security_detections": security_frames,
                "collaboration_detections": collab_frames,
            }

        return {
            "timeline": fused,
            "audio_windows": audio_windows,
            "contradictions": contradictions,
            "trends": trends,
            "summary": summary,
            "screen_content_summary": screen_content_summary,
        }


fusion_service = FusionService()
