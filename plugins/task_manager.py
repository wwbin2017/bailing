import logging
import importlib
import pkgutil
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from dotenv import load_dotenv
from pathlib import Path

from plugins.registry import function_registry, Action, ActionResponse, ToolType
from bailing.utils import read_json_file
import logging
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent  # 如果在 plugins/ 中，需要两级 parent
dotenv_path = BASE_DIR / "config" / ".env"
load_dotenv(dotenv_path=dotenv_path)


def auto_import_modules(package_name):
    """
    自动导入指定包内的所有模块。

    Args:
        package_name (str): 包的名称，如 'functions'。
    """
    # 获取包的路径
    package = importlib.import_module(package_name)
    package_path = package.__path__

    # 遍历包内的所有模块
    for _, module_name, _ in pkgutil.iter_modules(package_path):
        # 导入模块
        try:
            full_module_name = f"{package_name}.{module_name}"
            importlib.import_module(full_module_name)
            logger.info(f"模块 '{full_module_name}' 已加载")
        except Exception as e:
            logger.error(f"模块 '{module_name}' 加载失败：{e}")

# 自动导入 'functions' 包中的所有模块
auto_import_modules('plugins.functions')


class TaskManager:
    def __init__(self, config, result_queue: queue.Queue):
        self.functions = read_json_file(config.get("functions_call_name", "function_calls_config.json"))
        aigc_enabled = config.get("aigc_enabled", False)
        if not aigc_enabled:
            self.functions = [item for item in self.functions if item["function"]["name"] != 'aigc']
        self.task_queue = queue.Queue()
        # 初始化线程池
        self.task_executor = ThreadPoolExecutor(max_workers=10)
        self.result_queue = result_queue

    def get_functions(self):
        return self.functions

    def process_task(self):
        def task_thread():
            while True:
                try:
                    # 从队列中取出已完成的任务
                    while not self.task_queue.empty():
                        future = self.task_queue.get()
                        if future.done():  # 检查任务是否完成
                            result = future.result()  # 获取任务结果
                            self.result_queue.put(result)
                        else:
                            self.task_queue.put(future)  # 如果没有完成，放回队列
                        time.sleep(1)
                except Exception as e:
                    logger.error(f"task_thread 处理出错: {e}")
                time.sleep(2)
        consumer_task = threading.Thread(target=task_thread, daemon=True)
        consumer_task.start()

    @staticmethod
    def call_function(func_name, *args, **kwargs):
        """
        通用函数调用方法

        :param func_name: 函数名称 (str)
        :param args: 函数的位置参数
        :param kwargs: 函数的关键字参数
        :return: 函数调用的结果
        """
        try:
            # 从注册器中获取函数
            if func_name in function_registry:
                func = function_registry[func_name]
                # 调用函数，并传递参数
                result = func(*args, **kwargs)
                return result
            else:
                raise ValueError(f"函数 '{func_name}' 未注册！")
        except Exception as e:
            return f"调用函数 '{func_name}' 时出错：{str(e)}"

    def tool_call(self, func_name, func_args) -> ActionResponse:
        if func_name not in function_registry:
            return ActionResponse(action=Action.NOTFOUND, result="没有找到相应函数", response=None)
        if isinstance(func_args, str):
            try:
                func_args = json.loads(func_args)
            except Exception as e:
                logger.error(f"{func_name}, {func_args}, {e}")
        func = function_registry[func_name]
        if func.action == ToolType.NONE: #  = (1, "调用完工具后，啥也不用管")
            future = self.task_executor.submit(self.call_function, func_name, **func_args)
            self.task_queue.put(future)
            return ActionResponse(action=Action.NONE, result=None, response=None)
        elif func.action == ToolType.WAIT: # = (2, "调用工具，等待函数返回")
            try:
                result = self.call_function( func_name, **func_args)
            except Exception as e:
                logger.error(f"{func_name}, {func_args}, {func_args}, {e}")
            return ActionResponse(action=Action.REQLLM, result=result.response, response=result.response)
        elif func.action == ToolType.SCHEDULER: # = (3, "定时任务，时间到了之后，直接回复")
            result = self.call_function(func_name, **func_args)
            return ActionResponse(action=Action.RESPONSE, result=result.response, response=result.response)
        elif func.action == ToolType.TIME_CONSUMING: #  = (4, "耗时任务，需要一定时间，后台运行有结果后再回复")
            future = self.task_executor.submit(self.call_function, func_name, **func_args)
            self.task_queue.put(future)
            return ActionResponse(action=Action.RESPONSE, result=None, response="您好，正在查询信息中，一会查询完我会告诉你哟")
        elif func.action == ToolType.ADD_SYS_PROMPT: #  = (5, "增加系统指定到对话历史中去")
            result = self.call_function(func_name, **func_args)
            return ActionResponse(action=Action.ADDSYSTEMSPEAK, result=result, response=None)
        else:
            result = self.call_function(func_name, **func_args)
            return ActionResponse(action=Action.REQLLM, result=result.response, response=result.response)

if __name__ == "__main__":
    a = TaskManager({}, queue.Queue())
    b = a.call_function("get_weather", **{"city": "zhejiang/hangzhou"})
    print(b.action, b.result, b.response)

    rsp = a.call_function("aigc", **{"query": "你可以做什么"})
    print(rsp.response, rsp.action, rsp.result)