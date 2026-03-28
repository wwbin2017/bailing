import sys
import asyncio
from plugins.registry import register_function, ToolType
from plugins.registry import ActionResponse, Action
import logging
import requests

logger = logging.getLogger(__name__)


def openclaw_solver(question: str) -> str:
    """
    调用本地 OpenClaw 处理复杂问题
    """

    url = "http://127.0.0.1:18789/v1/responses"

    headers = {
        "Authorization": "Bearer YOUR_TOKEN",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "openclaw:main",
        "input": question
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        data = resp.json()

        # 👉 根据 OpenClaw 返回结构提取
        if "output" in data:
            return str(data["output"])
        if "answer" in data:
            return data["answer"]

        return str(data)

    except Exception as e:
        return f"[OpenClaw调用失败]: {str(e)}"

@register_function('aigc', ToolType.TIME_CONSUMING)
def aigc(prompt: str):
    """
    "可以帮你做任何事情的，通用aigc",
    """
    logger.warning("Processing your request...")
    result = openclaw_solver(prompt)
    logger.info("Request processing completed.")
    return ActionResponse(Action.REQLLM, result, f"好的，正在帮您处理{prompt}，处理完会通知您的哦！")

if __name__ == "__main__":
    rsp = aigc("帮我查一下关于manus的信息，并写一篇报告，保存到本地")
    print(rsp.response, rsp.action, rsp.result)