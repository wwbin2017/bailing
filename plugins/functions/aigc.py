from plugins.registry import register_function, ToolType
from plugins.registry import ActionResponse, Action
import requests
import os

url = "http://127.0.0.1:18789/v1/chat/completions"
OPENCLAW_AUTH = os.getenv("OPENCLAW_AUTH")
SESSION_ID = os.getenv("SESSION_ID")
OPENCLAW_URL = os.getenv("OPENCLAW_URL", url)

def openclaw_solver(query: str) -> str:
    """
    调用本地 OpenClaw 处理复杂问题
    """
    headers = {
        "Authorization": f"Bearer {OPENCLAW_AUTH}",
        "Content-Type": "application/json"
    }

    payload ={
     "model": "openclaw",
     "messages": [{"role": "user", "content": query}],
     "user":SESSION_ID,
     "stream": False
    }

    try:
        resp = requests.post(OPENCLAW_URL, headers=headers, json=payload, timeout=60000)
        data = resp.json()
        print(data)
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[aigc调用失败]: {str(e)}"

@register_function('aigc', ToolType.TIME_CONSUMING)
def aigc(query: str):
    """
    "可以帮你做任何事情的，通用aigc",
    """
    result = openclaw_solver(query)
    return ActionResponse(Action.REQLLM, result, f"好的，正在帮您处理{query}，处理完会通知您的哦！")

if __name__ == "__main__":
    rsp = aigc("你好")
    print(rsp.response, rsp.action, rsp.result)