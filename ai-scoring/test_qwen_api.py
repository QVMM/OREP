#!/usr/bin/env python3
"""测试 Qwen API 连接"""
import asyncio
import os
import sys

sys.path.insert(0, '/Users/liuyixing/项目/OREP/ai-scoring')

from app.services.ppt.qwen_client import QwenClient
from dotenv import load_dotenv

load_dotenv()


async def test_api():
    print("测试 Qwen API...")

    client = QwenClient(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )

    try:
        response = await client.chat(
            "请回复 JSON 格式：{\"status\": \"ok\", \"message\": \"API 正常工作\"}",
            system_prompt="你是一个JSON助手",
            json_mode=True,
            max_tokens=100
        )
        print(f"✅ API 响应: {response}")
    except Exception as e:
        print(f"❌ API 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_api())
