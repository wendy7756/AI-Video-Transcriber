"""OpenAI-compatible chat completion that never returns an empty answer silently."""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

# 推理模型的思考 token 也计入 max_tokens；被耗光时放宽上限重试一次。
# 8192 是多数 OpenAI 兼容服务（如 DeepSeek）单次输出的上限。
LENGTH_RETRY_MAX_TOKENS = 8192


class EmptyLLMResponse(Exception):
    """HTTP 200 但 message.content 为空（如推理模型把 max_tokens 全花在思考上）。"""


async def complete_text(client, *, model: str, messages: list, max_tokens: int, temperature: float) -> str:
    """调用 chat/completions 并返回非空正文；两次都为空时抛出 EmptyLLMResponse。

    空字符串不是异常，若直接返回会绕过调用方所有的 except 兜底，
    让空文稿一路流进输出文件。这里统一转成异常，交给调用方现有的降级逻辑。

    OpenAI SDK 是同步客户端，放进线程执行，否则一次几十秒的调用会卡住整个事件循环，
    任务进度推送（SSE）和状态查询都会停摆。
    """
    tokens = max_tokens
    finish_reason = None
    for attempt in (1, 2):
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=model,
            messages=messages,
            max_tokens=tokens,
            temperature=temperature,
        )
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        if content:
            return content

        finish_reason = getattr(choice, "finish_reason", None)
        logger.warning(
            f"LLM 返回空内容 (第 {attempt} 次, model={model}, max_tokens={tokens}, "
            f"finish_reason={finish_reason}, "
            f"reasoning_content={'有' if getattr(choice.message, 'reasoning_content', None) else '无'})"
        )
        if finish_reason == "length":
            tokens = max(tokens, min(tokens * 2, LENGTH_RETRY_MAX_TOKENS))

    raise EmptyLLMResponse(f"LLM 连续两次返回空内容 (model={model}, finish_reason={finish_reason})")
