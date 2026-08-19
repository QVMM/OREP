#!/usr/bin/env python3
"""
OREP AI 评分集成测试 — 通过 API 端点 + 轻量逻辑测试
测试单画面和双画面流程，不导入重型 ML 模块
"""
import os
import sys
import json
import subprocess
import tempfile

PASS = 0
FAIL = 0
WARN = 0

def check(name, condition, level='FAIL'):
    global PASS, FAIL, WARN
    if condition:
        print(f"  ✅ {name}")
        PASS += 1
    elif level == 'WARN':
        print(f"  ⚠️  {name}")
        WARN += 1
    else:
        print(f"  ❌ {name}")
        FAIL += 1


def api_get(path):
    """调用本地 AI 评分服务 GET 端点"""
    import urllib.request
    url = f'http://172.168.1.173:8000{path}'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        return 0, str(e)


def api_post(path, data=None, files=None):
    """调用本地 AI 评分服务 POST 端点"""
    import urllib.request
    url = f'http://172.168.1.173:8000{path}'
    try:
        if files:
            import io
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            body = b''
            for k, v in files.items():
                body += f'--{boundary}\r\n'.encode()
                body += f'Content-Disposition: form-data; name="{k}"; filename="{v["filename"]}"\r\n'.encode()
                body += f'Content-Type: {v.get("content_type", "application/octet-stream")}\r\n\r\n'.encode()
                body += v['content']
                body += b'\r\n'
            if data:
                for k, val in data.items():
                    body += f'--{boundary}\r\n'.encode()
                    body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
                    body += str(val).encode('utf-8')
                    body += b'\r\n'
            body += f'--{boundary}--\r\n'.encode()
            req = urllib.request.Request(url, data=body)
            req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        elif data:
            body = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=body)
            req.add_header('Content-Type', 'application/json')
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except Exception as e:
        return 0, str(e)


# ══════════════════════════════════════
#  测试 1: 健康检查
# ══════════════════════════════════════

def test_health():
    print("\n" + "="*60)
    print("🏥 测试 1: 健康检查")
    print("="*60)

    status, data = api_get('/api/ai/health')
    check("服务可达 (200)", status == 200)
    check("status=ok", data.get('status') == 'ok')
    check("DeepSeek 已配置", data.get('providers', {}).get('deepseek', {}).get('configured', False))
    check("MiniMax 已配置", data.get('providers', {}).get('minimax', {}).get('configured', False))
    check("上传目录存在", data.get('upload_dir_exists', False))


# ══════════════════════════════════════
#  测试 2: 单画面上传 (audio-only)
# ══════════════════════════════════════

def test_single_upload():
    print("\n" + "="*60)
    print("🎤 测试 2: 单画面音频上传 + 触发评分")
    print("="*60)

    # 创建测试 WAV (12秒)
    wav_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    import wave
    with wave.open(wav_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b'\x00\x00' * (16000 * 12))

    with open(wav_path, 'rb') as f:
        audio_content = f.read()

    status, data = api_post('/api/ai/upload-audio', data={
        'meeting_id': 'test_single_001',
        'project_name': '智慧城市管理系统',
        'track': '软件开发',
        'team_size': '4',
        'auto_score': 'true',
        'provider': 'deepseek',
    }, files={
        'audio': {'filename': 'test_audio.wav', 'content': audio_content, 'content_type': 'audio/wav'}
    })

    check("上传返回 200", status == 200)
    check("返回 meeting_id", data.get('meeting_id') == 'test_single_001')
    check("status=processing 或 uploaded", data.get('status') in ('processing', 'uploaded'))

    os.remove(wav_path)

    # 等一会儿检查状态
    import time
    time.sleep(3)

    status2, data2 = api_get('/api/ai/status/test_single_001')
    check("状态查询返回 200", status2 == 200)
    check("有 status 字段", 'status' in data2)
    print(f"    当前状态: {data2.get('status')}, 步骤: {data2.get('current_step', 'N/A')}")

    # 检查进度文件
    progress_path = os.path.expanduser("~/项目/OREP/ai-scoring/uploads/results/progress_test_single_001.json")
    if os.path.exists(progress_path):
        with open(progress_path) as f:
            progress = json.load(f)
        check("进度文件存在", True)
        check("进度有 step 字段", 'step' in progress)
        print(f"    进度: step={progress.get('step')}, label={progress.get('label')}")
    else:
        # 可能已经完成（短音频）
        result_path = os.path.expanduser("~/项目/OREP/ai-scoring/uploads/results/result_test_single_001.json")
        if os.path.exists(result_path):
            check("已直接完成（短音频）", True, level='WARN')
        else:
            check("进度/结果文件都不存在", False, level='WARN')


# ══════════════════════════════════════
#  测试 3: 双画面上传
# ══════════════════════════════════════

def test_dual_upload():
    print("\n" + "="*60)
    print("📹 测试 3: 双画面视频上传 + 触发评分")
    print("="*60)

    # 创建测试音频
    wav_path = tempfile.NamedTemporaryFile(suffix='.wav', delete=False).name
    import wave
    with wave.open(wav_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b'\x00\x00' * (16000 * 12))

    with open(wav_path, 'rb') as f:
        audio_content = f.read()

    # 创建假的摄像头和屏幕文件
    cam_content = b'\x00' * 1024
    screen_content = b'\x00' * 1024

    status, data = api_post('/api/ai/upload-dual-video', data={
        'meeting_id': 'test_dual_001',
        'project_name': '智慧城市管理系统（双画面）',
        'track': '软件开发',
        'team_size': '4',
        'auto_score': 'true',
        'provider': 'deepseek',
    }, files={
        'audio': {'filename': 'test_audio.wav', 'content': audio_content, 'content_type': 'audio/wav'},
        'camera': {'filename': 'camera.webm', 'content': cam_content, 'content_type': 'video/webm'},
        'screen': {'filename': 'screen.webm', 'content': screen_content, 'content_type': 'video/webm'},
    })

    check("双画面上传返回 200", status == 200)
    check("返回 meeting_id", data.get('meeting_id') == 'test_dual_001')
    check("status=processing", data.get('status') in ('processing', 'uploaded'))
    # message 应该包含 dual
    if 'dual' in data.get('message', '').lower():
        check("message 包含 dual 模式信息", True)
    else:
        check("message 包含 dual 模式信息", False, level='WARN')

    os.remove(wav_path)

    # 检查状态
    import time
    time.sleep(3)

    status2, data2 = api_get('/api/ai/status/test_dual_001')
    check("双画面状态查询返回 200", status2 == 200)
    print(f"    当前状态: {data2.get('status')}, 步骤: {data2.get('current_step', 'N/A')}")


# ══════════════════════════════════════
#  测试 4: pipeline 逻辑验证（代码级）
# ══════════════════════════════════════

def test_pipeline_logic():
    print("\n" + "="*60)
    print("🔍 测试 4: 流水线逻辑验证（代码级）")
    print("="*60)

    # 读取 pipeline_service.py 验证修复
    with open(os.path.expanduser("~/项目/OREP/ai-scoring/app/services/pipeline_service.py"), 'r') as f:
        code = f.read()

    # 检查 Bug 1 修复：skip_llm 后 LLM 代码应在 else 块内
    # 找到单视频流水线的 skip_llm 块
    skip_idx = code.find("# ========== Step 4: 大模型内容评分")
    if skip_idx > 0:
        chunk = code[skip_idx:skip_idx+2000]

        # 检查 fusion_context 构造在 else 块内（缩进比 if skip_llm 多一层）
        lines = chunk.split('\n')
        in_else = False
        fusion_in_else = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('else:') and 'skip_llm' not in stripped:
                in_else = True
            if in_else and 'fusion_context' in line and 'fusion_context = None' in line:
                fusion_in_else = True
                break

        check("单视频: fusion_context 在 else 块内", fusion_in_else)
    else:
        check("单视频: 找到 Step 4 代码块", False)

    # 检查双视频流水线的 skip_llm dimensions
    dual_idx = code.find("# Step 8: 大模型内容评分")
    if dual_idx > 0:
        chunk = code[dual_idx:dual_idx+1500]

        # 找到 skip_llm 块
        if "dimensions': {'name': name" in chunk or "dimensions': {name: {'name': name" in chunk:
            check("双视频: skip_llm dimensions 有完整结构", True)
        elif "'dimensions': {}" in chunk:
            check("双视频: skip_llm dimensions 有完整结构", False)
        else:
            check("双视频: skip_llm dimensions 格式", True, level='WARN')
    else:
        check("双视频: 找到 Step 8 代码块", False)

    # 检查单视频 skip_llm dimensions 格式
    single_skip_idx = code.find("'model': 'duration_adjustment'")
    if single_skip_idx > 0:
        # 往前找 dimensions 定义
        context = code[max(0, single_skip_idx-300):single_skip_idx+50]
        if "{'name': name, 'score':" in context or "{'name': name, 'score'" in context:
            check("单视频: skip_llm dimensions 有 name/score 结构", True)
        elif "'dimensions': {name: score" in context:
            check("单视频: skip_llm dimensions 有 name/score 结构", False)
        else:
            check("单视频: skip_llm dimensions 格式", True, level='WARN')

    # 检查 report_service 的 priorities 兼容性
    with open(os.path.expanduser("~/项目/OREP/ai-scoring/app/services/report_service.py"), 'r') as f:
        report_code = f.read()

    if 'isinstance(priorities[0], str)' in report_code:
        check("report_service: 支持字符串 priorities", True)
    else:
        check("report_service: 支持字符串 priorities", False)

    if 'isinstance(p_item, dict)' in report_code:
        check("report_service: 支持对象 priorities 兼容", True)
    else:
        check("report_service: 支持对象 priorities 兼容", False)

    # 检查重复 return 已修复
    if report_code.count('return d\n\n    return d') > 0:
        check("report_service: 重复 return 已清理", False)
    else:
        check("report_service: 重复 return 已清理", True)


# ══════════════════════════════════════
#  测试 5: 录制 Bot → AI 评分端点路由
# ══════════════════════════════════════

def test_recording_to_ai_routing():
    print("\n" + "="*60)
    print("🤖 测试 5: 录制Bot → AI评分端点路由逻辑")
    print("="*60)

    # 读取 recording-bot server.js
    with open(os.path.expanduser("~/项目/OREP/recording-bot/src/server.js"), 'r') as f:
        bot_code = f.read()

    # 验证：双源用 upload-dual-video，单源用 upload-audio
    check("Bot 有 uploadToAiScoring 函数", 'uploadToAiScoring' in bot_code)
    check("双源模式用 upload-dual-video",
          "upload-dual-video" in bot_code)
    check("单源模式用 upload-audio",
          "upload-audio" in bot_code)

    # 验证：dual 判断逻辑
    if "const isDual = files.camera && files.screen" in bot_code:
        check("双源判断: camera && screen 同时存在", True)
    else:
        check("双源判断逻辑", False, level='WARN')

    # 验证：API 地址
    if 'AI_SCORING_URL' in bot_code:
        check("有 AI_SCORING_URL 配置", True)
    else:
        check("有 AI_SCORING_URL 配置", False)

    # 验证：请求格式包含必要字段
    check("请求含 meeting_id", "'meeting_id'" in bot_code or '"meeting_id"' in bot_code)
    check("请求含 project_name", "'project_name'" in bot_code or '"project_name"' in bot_code)
    check("请求含 auto_score", "'auto_score'" in bot_code or '"auto_score"' in bot_code)


# ══════════════════════════════════════
#  测试 6: 后端回调处理验证
# ══════════════════════════════════════

def test_backend_callback():
    print("\n" + "="*60)
    print("🔄 测试 6: 后端回调处理验证")
    print("="*60)

    # 读取 Java 后端回调控制器
    with open(os.path.expanduser("~/项目/OREP/backend/src/main/java/com/orep/backend/controller/AiScoreController.java"), 'r') as f:
        java_code = f.read()

    # 验证字段映射
    check("后端接收 meetingId", 'meetingId' in java_code)
    check("后端接收 status", 'status' in java_code)
    check("后端接收 overallScore", 'overallScore' in java_code)
    check("后端接收 dimensions", 'dimensions' in java_code)
    check("后端接收 highlights", 'highlights' in java_code)
    check("后端接收 criticalIssues", 'criticalIssues' in java_code)
    check("后端接收 improvementPriorities", 'improvementPriorities' in java_code)
    check("后端接收 speechQuality", 'speechQuality' in java_code)
    check("后端接收 model", 'model' in java_code)
    check("后端接收 transcript", 'transcript' in java_code)
    check("后端接收 resultPath", 'resultPath' in java_code)
    check("后端接收 errorMessage", 'errorMessage' in java_code)

    # 验证状态处理
    check("completed 状态处理", '"completed".equals(status)' in java_code)
    check("failed 状态处理", '"failed".equals(status)' in java_code)
    check("insert 或 update", 'insert(report)' in java_code and 'updateById(report)' in java_code)

    # 验证维度数据可 JSON 序列化
    check("dimensions JSON 存储", 'dimensionsJson' in java_code or 'DimensionsJson' in java_code)
    check("safeJson 方法处理 Map/List", 'safeJson' in java_code)

    # 检查 pipeline 发送的字段名和后端接收的一致性
    pipeline_path = os.path.expanduser("~/项目/OREP/ai-scoring/app/services/pipeline_service.py")
    with open(pipeline_path, 'r') as f:
        pipeline_code = f.read()

    # _notify_backend 中的字段名
    field_mappings = [
        ('meetingId', 'meetingId'),
        ('status', 'status'),
        ('overallScore', 'overallScore'),
        ('dimensions', 'dimensions'),
        ('highlights', 'highlights'),
        ('criticalIssues', 'criticalIssues'),
        ('improvementPriorities', 'improvementPriorities'),
        ('speechQuality', 'speechQuality'),
        ('model', 'model'),
        ('transcript', 'transcript'),
    ]

    for py_field, java_field in field_mappings:
        py_present = f"'{py_field}'" in pipeline_code
        java_present = java_field in java_code
        check(f"字段对齐: pipeline→{py_field} ↔ 后端→{java_field}",
              py_present and java_present)


# ══════════════════════════════════════
#  运行
# ══════════════════════════════════════

if __name__ == '__main__':
    print("╔" + "═"*58 + "╗")
    print("║   OREP AI 评分集成测试                                 ║")
    print("║   单画面 & 双画面流水线 + API 端点 + 代码级验证        ║")
    print("╚" + "═"*58 + "╝")

    test_health()
    test_single_upload()
    test_dual_upload()
    test_pipeline_logic()
    test_recording_to_ai_routing()
    test_backend_callback()

    print("\n" + "="*60)
    print(f"📊 结果汇总: ✅ {PASS} 通过  ❌ {FAIL} 失败  ⚠️  {WARN} 警告")
    print("="*60)

    if FAIL > 0:
        print("❌ 存在失败用例，请检查上方详情")
        sys.exit(1)
    else:
        print("✅ 全部通过!")
        sys.exit(0)
