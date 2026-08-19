"""
视频分析服务
从视频中抽取关键帧，用多模态大模型分析：
1. 演讲者表现（肢体语言/表情/眼神）
2. 屏幕/PPT内容（文字、图表、代码、标准文档等）
3. 团队协作状态
"""
import os
import json
import logging
import base64
import subprocess
import tempfile
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


def sample_evenly(items: list[dict], max_items: int, key=None) -> list[dict]:
    """Keep a timeline-sized list evenly covered from first item to last item."""
    if max_items <= 0:
        return []
    if len(items) <= max_items:
        return items

    ordered = sorted(items, key=key) if key else list(items)
    if max_items == 1:
        return [ordered[0]]

    last_index = len(ordered) - 1
    return [
        ordered[round(index * last_index / (max_items - 1))]
        for index in range(max_items)
    ]


class VideoAnalysisService:
    """视频分析：抽帧 → 多模态模型分析 → 输出结构化结果（含PPT/屏幕内容识别）"""

    def __init__(self):
        self.client = None
        self._client_lock = threading.Lock()
        self.model = settings.VIDEO_MODEL  # qwen3-vl-flash
        self.batch_size = settings.VIDEO_BATCH_SIZE  # 4；8 帧加大提示会把通义视觉打超时
        self.frame_interval = settings.VIDEO_FRAME_INTERVAL  # 30秒
        self._timeout_streak = 0

    def _client(self) -> OpenAI:
        if not settings.DASHSCOPE_API_KEY:
            raise RuntimeError("DASHSCOPE_API_KEY 未配置，无法进行视频视觉分析")
        if self.client is None:
            with self._client_lock:
                if self.client is None:
                    self.client = OpenAI(
                        api_key=settings.DASHSCOPE_API_KEY,
                        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                        timeout=float(getattr(settings, "VIDEO_ANALYSIS_TIMEOUT_SECONDS", 90) or 90),
                        max_retries=int(getattr(settings, "VIDEO_ANALYSIS_MAX_RETRIES", 1) or 0),
                    )
        return self.client

    @staticmethod
    def _is_timeout_error(exc: BaseException) -> bool:
        text = f"{type(exc).__name__} {exc}".lower()
        return "timeout" in text or "timed out" in text

    def extract_keyframes(self, video_path: str, interval_sec: Optional[int] = None) -> list[str]:
        """
        从视频中按固定间隔抽取关键帧
        返回帧图片路径列表
        """
        interval = interval_sec or self.frame_interval

        # 创建临时目录存放帧
        frame_dir = os.path.join(os.path.dirname(video_path), "_frames")
        os.makedirs(frame_dir, exist_ok=True)

        # 清理旧帧
        for f in os.listdir(frame_dir):
            if f.startswith("frame_") and f.endswith(".jpg"):
                os.remove(os.path.join(frame_dir, f))

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps=1/{interval},scale=720:-1",
            "-q:v", "3",
            os.path.join(frame_dir, "frame_%03d.jpg"),
            "-y"
        ]

        logger.info(f"抽取关键帧: interval={interval}s")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"ffmpeg 抽帧失败: {result.stderr}")
            raise RuntimeError(f"视频抽帧失败: {result.stderr[:200]}")

        frames = sorted([
            os.path.join(frame_dir, f)
            for f in os.listdir(frame_dir)
            if f.startswith("frame_") and f.endswith(".jpg")
        ])

        logger.info(f"抽取完成: {len(frames)} 帧")
        return frames

    def _encode_image(self, path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def _build_prompt(self, frame_indices: list[int], timestamps: list[int]) -> str:
        nums = ", ".join(str(i) for i in frame_indices)
        times = ", ".join(str(t) for t in timestamps)

        return f"""你是路演表现与内容分析师。以下是同一场路演视频在不同时间点的截图（帧序号：{nums}；对应时间点分钟：{times}，按时间顺序排列）。
请对每张截图进行**两部分分析**：演讲者表现 + 屏幕/内容识别。

## 第一部分：演讲者表现分析

对每张图分析：
1. **肢体语言**：手势使用、姿态（站/坐/端正/前倾）、整体表达（僵硬/自然/活跃）→ 打分1-10
2. **面部表情**：自信/紧张/平淡/微笑，是否有紧张表现 → 自信度1-10
3. **眼神方向**：看向镜头/观众/屏幕/稿件 → 打分1-10
4. **场景**：演讲/演示/讨论/答辩，画面人数
5. **当前发言人**：画面中谁在说话？描述其位置、衣着特征、状态。其他成员在做什么？

## 第二部分：屏幕/内容识别（关键！用于评分证据提取）

仔细观察截图中的**屏幕内容、PPT、投影画面**，识别以下信息：

1. **屏幕类型**：PPT幻灯片 / 代码编辑器 / 浏览器网页 / 终端命令行 / 数据库管理工具 / 设计软件 / 无屏幕 / 其他
2. **PPT标题**：如果当前页面是PPT，识别其标题文字（精确到可见文字）
3. **PPT内容类型**（可多选）：
   - "项目介绍" — 项目背景、团队介绍等
   - "技术架构" — 系统架构图、技术栈说明
   - "标准规范" — 国家标准、行业标准、开发规范文档截图或条款
   - "功能演示" — 功能截图、界面展示
   - "数据图表" — 统计图表、数据可视化、对比表格
   - "代码展示" — 源代码片段
   - "测试结果" — 测试报告、覆盖率、性能数据
   - "成本分析" — 成本表格、ROI计算
   - "创新点说明" — 创新对比、方案对比
   - "安全方案" — 安全架构、加密方案、权限设计
   - "团队分工" — 分工表、角色说明
   - "未来规划" — 路线图、迭代计划
   - "开源声明" — License、开源组件列表
   - "其他"
4. **可见文字摘要**：提取屏幕/PPT上可见的关键文字（标准编号如"GB/T XXXX"、技术名词、数据指标等），最多100字
5. **是否有代码**：画面中是否展示源代码？如有，简述是什么语言/框架的代码
6. **是否有数据/图表**：是否有数据表格、柱状图、折线图等？如有，简述数据内容
7. **团队协作**：是否有多人同时在画面中？是否有分工展示、协作场景？

**严格输出 JSON 数组**，每张图一个对象，按顺序排列：
[
  {{
    "frame": 1,
    "timestamp_min": 0,
    "gesture": {{"desc": "手势自然，双手配合讲解", "score": 7}},
    "posture": {{"desc": "站姿端正，微微前倾", "score": 8}},
    "expression": {{"desc": "面带微笑，表情自信", "confidence": 7}},
    "eye_contact": {{"direction": "屏幕", "score": 5}},
    "scene": {{"type": "演示", "has_screen_share": true, "people_count": 1}},
    "active_speaker": {{"description": "短发男生，穿白色衬衫，站在屏幕左侧", "other_members": [{{"position": "坐在后排", "status": "在看电脑"}}]}},
    "screen_content": {{
      "screen_type": "PPT幻幻灯片",
      "ppt_title": "系统架构设计",
      "content_types": ["技术架构", "功能演示"],
      "visible_text_summary": "展示微服务架构图，包含用户服务、订单服务、网关三个模块，使用Spring Cloud",
      "has_code": false,
      "has_data_chart": true,
      "chart_desc": "柱状图展示QPS对比：优化前500 QPS，优化后2000 QPS"
    }},
    "team_collaboration": {{
      "multi_person_visible": true,
      "collab_type": "分工展示",
      "desc": "屏幕显示团队分工表：前端2人、后端2人、测试1人"
    }},
    "impression": "正在讲解技术架构，PPT展示了清晰的微服务设计图"
  }},
  ...
]
不要输出JSON之外的任何文字。"""

    def _analyze_batch(
        self,
        frame_paths: list[str],
        start_index: int,
        timestamps_sec: Optional[list[float]] = None
    ) -> tuple[list[dict], dict]:
        """分析一批帧，返回结果列表和token用量"""
        content = []
        for fp in frame_paths:
            img_b64 = self._encode_image(fp)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })

        frame_nums = [start_index + i + 1 for i in range(len(frame_paths))]
        if timestamps_sec:
            timestamps = [round(t / 60, 1) for t in timestamps_sec]
        else:
            timestamps = [(start_index + i) * self.frame_interval // 60 for i in range(len(frame_paths))]

        content.append({
            "type": "text",
            "text": self._build_prompt(frame_nums, timestamps)
        })

        response = self._client().chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            temperature=0.1,
            max_tokens=6000,  # 增大输出限制（含屏幕内容分析）
        )

        result_text = response.choices[0].message.content.strip()
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()

        results = json.loads(result_text)
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens
        }

        return results, usage

    def analyze_frames(
        self,
        frame_paths: list[str],
        timestamps_sec: Optional[list[float]] = None,
        progress_callback=None,
        max_workers: Optional[int] = None,
    ) -> tuple[list[dict], dict]:
        """批量分析所有帧"""
        total_tokens = {"prompt": 0, "completion": 0}
        total_frames = len(frame_paths)
        if not frame_paths:
            return [], total_tokens

        batches = []
        for i in range(0, total_frames, self.batch_size):
            batch = frame_paths[i:i + self.batch_size]
            batch_end = min(i + self.batch_size, len(frame_paths))
            batch_timestamps = timestamps_sec[i:i + self.batch_size] if timestamps_sec else None
            batches.append((i, batch_end, batch, batch_timestamps))

        worker_count = min(
            max(1, max_workers or settings.VIDEO_ANALYSIS_MAX_WORKERS),
            len(batches),
        )
        with self._client_lock:
            self._timeout_streak = 0
        logger.info("视觉批次有限并发: batches=%s workers=%s", len(batches), worker_count)
        completed_frames = 0
        results_by_start = {}
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="video-batch") as executor:
            future_map = {}
            for start, batch_end, batch, batch_timestamps in batches:
                logger.info(f"分析帧 {start + 1}-{batch_end}...")
                future = executor.submit(
                    self._analyze_batch_with_recovery,
                    batch,
                    start,
                    batch_timestamps,
                )
                future_map[future] = (start, len(batch))

            for future in as_completed(future_map):
                start, batch_length = future_map[future]
                results, usage = future.result()
                results_by_start[start] = results
                completed_frames += batch_length
                total_tokens["prompt"] += usage["prompt_tokens"]
                total_tokens["completion"] += usage["completion_tokens"]
                if progress_callback:
                    try:
                        progress_callback(completed_frames, total_frames)
                    except Exception as e:
                        logger.warning(f"视频分析进度回调失败: {e}")

        all_results = []
        for start in sorted(results_by_start):
            results = results_by_start[start]
            all_results.extend(results)

        return all_results, total_tokens

    def _analyze_batch_with_recovery(
        self,
        batch: list[str],
        start_index: int,
        timestamps_sec: Optional[list[float]] = None
    ) -> tuple[list[dict], dict]:
        """Analyze a batch; on failure split in half, then singles. Abort after a timeout streak."""
        total_tokens = {"prompt_tokens": 0, "completion_tokens": 0}
        abort_after = int(getattr(settings, "VIDEO_ANALYSIS_TIMEOUT_STREAK_ABORT", 6) or 6)
        try:
            result = self._analyze_batch(batch, start_index, timestamps_sec)
            with self._client_lock:
                self._timeout_streak = 0
            return result
        except Exception as e:
            timed_out = self._is_timeout_error(e)
            with self._client_lock:
                if timed_out:
                    self._timeout_streak += 1
                    streak = self._timeout_streak
                else:
                    self._timeout_streak = 0
                    streak = 0
            logger.error(
                "帧 %s-%s 批量分析失败，将拆分重试: %s",
                start_index + 1,
                start_index + len(batch),
                e,
            )
            if timed_out and streak >= abort_after:
                logger.error("视觉接口连续超时 %s 次，停止继续打通义，避免空转", streak)
                return (
                    [
                        {
                            "error": f"vision_timeout_circuit:{e}",
                            "frame": start_index + offset + 1,
                            "timestamp_min": round(
                                ((timestamps_sec[offset] if timestamps_sec and offset < len(timestamps_sec) else 0) / 60),
                                1,
                            ),
                            "image_path": frame_path,
                        }
                        for offset, frame_path in enumerate(batch)
                    ],
                    total_tokens,
                )

        if len(batch) > 2:
            mid = len(batch) // 2
            left_ts = timestamps_sec[:mid] if timestamps_sec else None
            right_ts = timestamps_sec[mid:] if timestamps_sec else None
            left, left_usage = self._analyze_batch_with_recovery(batch[:mid], start_index, left_ts)
            right, right_usage = self._analyze_batch_with_recovery(
                batch[mid:], start_index + mid, right_ts
            )
            total_tokens["prompt_tokens"] += left_usage.get("prompt_tokens", 0) + right_usage.get("prompt_tokens", 0)
            total_tokens["completion_tokens"] += left_usage.get("completion_tokens", 0) + right_usage.get("completion_tokens", 0)
            return left + right, total_tokens

        recovered = []
        for offset, frame_path in enumerate(batch):
            frame_no = start_index + offset + 1
            single_ts = [timestamps_sec[offset]] if timestamps_sec and offset < len(timestamps_sec) else None
            try:
                result, usage = self._analyze_batch([frame_path], start_index + offset, single_ts)
                with self._client_lock:
                    self._timeout_streak = 0
                recovered.extend(result)
                total_tokens["prompt_tokens"] += usage.get("prompt_tokens", 0)
                total_tokens["completion_tokens"] += usage.get("completion_tokens", 0)
            except Exception as single_error:
                if self._is_timeout_error(single_error):
                    with self._client_lock:
                        self._timeout_streak += 1
                        streak = self._timeout_streak
                    if streak >= abort_after:
                        logger.error("视觉接口连续超时 %s 次，剩余单帧不再请求", streak)
                        recovered.append({
                            "error": f"vision_timeout_circuit:{single_error}",
                            "frame": frame_no,
                            "timestamp_min": round((single_ts[0] if single_ts else 0) / 60, 1),
                            "image_path": frame_path,
                        })
                        for rest_offset, rest_path in enumerate(batch[offset + 1 :], start=offset + 1):
                            rest_ts = timestamps_sec[rest_offset] if timestamps_sec and rest_offset < len(timestamps_sec) else 0
                            recovered.append({
                                "error": "vision_timeout_circuit:skipped",
                                "frame": start_index + rest_offset + 1,
                                "timestamp_min": round((rest_ts or 0) / 60, 1),
                                "image_path": rest_path,
                            })
                        break
                logger.error(f"帧 {frame_no} 单帧分析失败: {single_error}")
                recovered.append({
                    "error": str(single_error),
                    "frame": frame_no,
                    "timestamp_min": round((single_ts[0] if single_ts else 0) / 60, 1),
                    "image_path": frame_path,
                })
        return recovered, total_tokens

    def run_analysis_on_frames(
        self,
        frame_items: list[dict],
        interval_sec: Optional[int] = None,
        progress_callback=None
    ) -> dict:
        """
        分析已经采集好的关键帧。
        frame_items: [{image_path, timestamp, frame_type, diff_score}]
        """
        interval = interval_sec or self.frame_interval
        valid_items = [
            item for item in frame_items
            if item.get("image_path") and os.path.exists(item.get("image_path"))
        ]
        frame_paths = [item["image_path"] for item in valid_items]
        timestamps = [float(item.get("timestamp") or 0) for item in valid_items]

        logger.info(f"开始分析已采集关键帧: {len(frame_paths)} 帧")
        results, tokens = self.analyze_frames(frame_paths, timestamps, progress_callback=progress_callback)

        for i, result in enumerate(results):
            if i >= len(valid_items):
                break
            item = valid_items[i]
            result["timestamp_min"] = round(float(item.get("timestamp") or 0) / 60, 1)
            result["frame_source"] = "session_capture"
            result["frame_type"] = item.get("frame_type", "")
            result["diff_score"] = item.get("diff_score", 0)
            result["image_path"] = item.get("image_path")

        aggregates = self._compute_aggregates(results)
        return {
            "frame_count": len(results),
            "interval_sec": interval,
            "per_frame": results,
            "aggregates": aggregates,
            "tokens_used": tokens,
            "source": "session_capture"
        }

    def _compute_aggregates(self, results: list[dict]) -> dict:
        """计算汇总统计（含屏幕内容汇总）"""
        valid = [r for r in results if "error" not in r]
        if not valid:
            return {"error": "无有效数据"}

        def avg(key, subkey):
            vals = [r[key][subkey] for r in valid if key in r and subkey in r.get(key, {})]
            return round(sum(vals) / len(vals), 1) if vals else 0

        # 眼神分布
        eye_dirs = {}
        for r in valid:
            d = r.get("eye_contact", {}).get("direction", "未知")
            eye_dirs[d] = eye_dirs.get(d, 0) + 1

        # 场景分布
        scene_types = {}
        for r in valid:
            t = r.get("scene", {}).get("type", "未知")
            scene_types[t] = scene_types.get(t, 0) + 1

        # 趋势数据
        gestures = [r.get("gesture", {}).get("score", 0) for r in valid]
        expressions = [r.get("expression", {}).get("confidence", 0) for r in valid]
        eyes = [r.get("eye_contact", {}).get("score", 0) for r in valid]

        # ========== 新增：屏幕内容汇总 ==========
        screen_types = {}
        all_content_types = {}
        all_visible_texts = []
        code_frames = []
        chart_frames = []
        standard_frames = []
        cost_frames = []
        security_frames = []
        collab_frames = []

        for r in valid:
            sc = r.get("screen_content", {})
            if not sc:
                continue

            # 屏幕类型统计
            st = sc.get("screen_type", "无")
            screen_types[st] = screen_types.get(st, 0) + 1

            # 内容类型统计
            for ct in sc.get("content_types", []):
                all_content_types[ct] = all_content_types.get(ct, 0) + 1

            # 可见文字收集
            vt = sc.get("visible_text_summary", "")
            if vt and vt != "无":
                all_visible_texts.append({
                    "frame": r.get("frame", 0),
                    "timestamp_min": r.get("timestamp_min", 0),
                    "text": vt
                })

            # 特殊内容标记
            if sc.get("has_code"):
                code_frames.append({
                    "frame": r.get("frame", 0),
                    "timestamp_min": r.get("timestamp_min", 0),
                    "desc": sc.get("visible_text_summary", "")
                })

            if sc.get("has_data_chart"):
                chart_frames.append({
                    "frame": r.get("frame", 0),
                    "timestamp_min": r.get("timestamp_min", 0),
                    "desc": sc.get("chart_desc", sc.get("visible_text_summary", ""))
                })

            if "标准规范" in sc.get("content_types", []):
                standard_frames.append({
                    "frame": r.get("frame", 0),
                    "timestamp_min": r.get("timestamp_min", 0),
                    "title": sc.get("ppt_title", ""),
                    "text": sc.get("visible_text_summary", "")
                })

            if "成本分析" in sc.get("content_types", []):
                cost_frames.append({
                    "frame": r.get("frame", 0),
                    "timestamp_min": r.get("timestamp_min", 0),
                    "text": sc.get("visible_text_summary", "")
                })

            if "安全方案" in sc.get("content_types", []):
                security_frames.append({
                    "frame": r.get("frame", 0),
                    "timestamp_min": r.get("timestamp_min", 0),
                    "text": sc.get("visible_text_summary", "")
                })

            # 团队协作
            tc = r.get("team_collaboration", {})
            if tc.get("multi_person_visible"):
                collab_frames.append({
                    "frame": r.get("frame", 0),
                    "timestamp_min": r.get("timestamp_min", 0),
                    "type": tc.get("collab_type", ""),
                    "desc": tc.get("desc", "")
                })

        return {
            # 原有字段
            "avg_gesture": avg("gesture", "score"),
            "avg_posture": avg("posture", "score"),
            "avg_expression": avg("expression", "confidence"),
            "avg_eye_contact": avg("eye_contact", "score"),
            "avg_visual_composite": round(
                (avg("gesture", "score") + avg("posture", "score") +
                 avg("expression", "confidence") + avg("eye_contact", "score")) / 4, 1
            ),
            "eye_direction_distribution": eye_dirs,
            "scene_type_distribution": scene_types,
            "trend_gesture": gestures,
            "trend_expression": expressions,
            "trend_eye_contact": eyes,
            "valid_frames": len(valid),
            "total_frames": len(results),
            # ========== 新增：屏幕内容汇总 ==========
            "screen_content_summary": {
                "screen_type_distribution": screen_types,
                "content_type_counts": all_content_types,
                "visible_texts": sample_evenly(
                    all_visible_texts,
                    120,
                    key=lambda item: float(item.get("timestamp_min") or 0)
                ),
                "code_detections": code_frames,
                "chart_detections": chart_frames,
                "standard_detections": standard_frames,
                "cost_detections": cost_frames,
                "security_detections": security_frames,
                "collaboration_detections": collab_frames,
                "has_ppt_evidence": len(all_content_types) > 0,
                "evidence_diversity_score": len(all_content_types),  # 证据多样性（内容类型数）
            }
        }

    def run_analysis(
        self,
        video_path: str,
        interval_sec: Optional[int] = None,
        progress_callback=None
    ) -> dict:
        """
        完整视频分析流水线
        返回: { frame_count, interval_sec, per_frame, aggregates, tokens_used }
        """
        interval = interval_sec or self.frame_interval
        logger.info(f"开始视频分析: {video_path}, interval={interval}s")

        frames = self.extract_keyframes(video_path, interval)
        results, tokens = self.analyze_frames(frames, progress_callback=progress_callback)
        aggregates = self._compute_aggregates(results)

        # 清理帧文件
        frame_dir = os.path.join(os.path.dirname(video_path), "_frames")
        if os.path.exists(frame_dir):
            shutil.rmtree(frame_dir, ignore_errors=True)

        return {
            "frame_count": len(results),
            "interval_sec": interval,
            "per_frame": results,
            "aggregates": aggregates,
            "tokens_used": tokens
        }


# 全局实例
video_analysis_service = VideoAnalysisService()
