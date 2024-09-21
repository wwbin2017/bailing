from enum import Enum
import logging

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化函数注册字典
function_registry = {}

def register_function(name):
    """注册函数到函数注册字典的装饰器"""
    def decorator(func):
        function_registry[name] = func
        logger.info(f"函数 '{name}' 注册成功")
        return func
    return decorator


class Action(Enum):
    NONE = (1,  "啥也不干")
    RESPONSE = (2, "直接回复")
    REQLLM = (3, "调用函数后再请求llm生成回复")
    ADDSYSTEM = (4, "添加系统prompt到对话中去")
    def __init__(self, code, message):
        self.code = code
        self.message = message

class ActionResponse:
    def __init__(self, action : Action, result, response):
        self.action = action
        self.result = result
        self.response = response



