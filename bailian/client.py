"""
bailian/client.py — 阿里云百炼 OpenAI 兼容客户端封装

依赖：openai>=1.50（用阿里云镜像装：python3 -m pip install --user -i https://mirrors.aliyun.com/pypi/simple/ openai）
Key 来源：~/.config/org-future-insights/.env (DASHSCOPE_API_KEY=sk-xxx)

使用：
    from bailian.client import get_client, chat
    resp = chat([{"role": "user", "content": "hi"}], model="qwen-max")
    print(resp.text, resp.input_tokens, resp.output_tokens)
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ENV_FILE = Path.home() / ".config" / "org-future-insights" / ".env"
BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 模型默认参数（qwen-max 最高质量；qwen-plus 性价比；qwen-turbo 最便宜）
DEFAULT_MODEL = "qwen-max"
DEFAULT_TIMEOUT = 120  # 长文本 + 复杂推理需要时间
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 5


def _load_env() -> dict[str, str]:
    """从 ~/.config/org-future-insights/.env 读取 key（不打印 key）"""
    if not ENV_FILE.exists():
        raise FileNotFoundError(
            f"❌ 未找到 {ENV_FILE}\n"
            f"请用以下命令创建：\n"
            f"  mkdir -p ~/.config/org-future-insights\n"
            f"  echo 'DASHSCOPE_API_KEY=sk-xxxx' > ~/.config/org-future-insights/.env\n"
            f"  chmod 600 ~/.config/org-future-insights/.env"
        )
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def get_api_key() -> str:
    env = _load_env()
    key = env.get("DASHSCOPE_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError("❌ DASHSCOPE_API_KEY 未配置")
    return key


def get_client():
    """返回 OpenAI 兼容客户端（指向阿里云百炼）"""
    from openai import OpenAI
    return OpenAI(api_key=get_api_key(), base_url=BAILIAN_BASE_URL, timeout=DEFAULT_TIMEOUT)


@dataclass
class ChatResponse:
    text: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    model: str
    elapsed_sec: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_length": len(self.text),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "elapsed_sec": round(self.elapsed_sec, 2),
        }


def chat(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.5,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> ChatResponse:
    """
    调用百炼 chat completion，含重试 + token 统计。

    response_format={"type": "json_object"} 可强制 JSON 返回（用于 classify 任务）
    """
    client = get_client()
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.time()
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            if response_format:
                kwargs["response_format"] = response_format
            resp = client.chat.completions.create(**kwargs)
            elapsed = time.time() - t0
            usage = resp.usage
            return ChatResponse(
                text=resp.choices[0].message.content or "",
                input_tokens=usage.prompt_tokens if usage else 0,
                output_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
                model=model,
                elapsed_sec=elapsed,
            )
        except Exception as e:
            last_err = e
            print(f"⚠️ chat 第 {attempt}/{MAX_RETRIES} 次失败: {type(e).__name__}: {str(e)[:200]}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SEC * attempt)
    raise RuntimeError(f"❌ 百炼调用 {MAX_RETRIES} 次全失败: {last_err}")


def smoke_test() -> bool:
    """10 token 接通测试，返回 True 表示可用"""
    print("🔍 百炼接通测试...")
    try:
        resp = chat(
            messages=[{"role": "user", "content": "回答两个字：你好"}],
            model="qwen-turbo",  # 用最便宜的模型测试
            max_tokens=10,
            temperature=0.1,
        )
        print(f"✅ 接通成功 | 模型: {resp.model} | tokens: {resp.input_tokens}→{resp.output_tokens} | 回复: {resp.text!r} | {resp.elapsed_sec:.2f}s")
        return True
    except Exception as e:
        print(f"❌ 接通失败: {e}")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if smoke_test() else 1)
