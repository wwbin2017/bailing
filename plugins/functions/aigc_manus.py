import sys
import asyncio
from plugins.registry import register_function, ToolType
from plugins.registry import ActionResponse, Action
import logging

logger = logging.getLogger(__name__)

sys.path.append("third_party/OpenManus")

from app.agent.manus import Manus

agent = Manus()

def parser_result(messages):
    if not isinstance(messages, list):
        return "任务执行失败"
    for message in reversed(messages):
        if message.role not in ("assistant"):
            continue
        if not message.content:
            continue
        return message.content

@register_function('aigc_manus', ToolType.TIME_CONSUMING)
def aigc_manus(prompt: str):
    """
    "可以帮你做任何事情的，通用aigc",
    """
    logger.warning("Processing your request...")
    asyncio.run(agent.run(prompt))
    logger.info("Request processing completed.")
    result = parser_result(agent.messages)
    return ActionResponse(Action.REQLLM, result, f"好的，正在帮您处理{prompt}，处理完会通知您的哦！")

if __name__ == "__main__":
    rsp = aigc_manus("帮我查一下关于manus的信息，并写一篇报告，保存到本地")
    print(rsp.response, rsp.action, rsp.result)