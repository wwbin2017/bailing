import logging
from plugins.registry import function_registry
import importlib
import pkgutil

logger = logging.getLogger(__name__)


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
        full_module_name = f"{package_name}.{module_name}"
        importlib.import_module(full_module_name)
        logger.info(f"模块 '{full_module_name}' 已加载")

# 自动导入 'functions' 包中的所有模块
auto_import_modules('functions')

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


def handle_function_call():
    func_name = "get_weather"
    args = {"city": "zhejiang/hangzhou"}
    if isinstance(args, dict):
        # 调用通用函数调用接口
        result = call_function(func_name, **args)
    else:
        result = args  # 如果解析错误，将错误信息返回
    return result


if __name__ == "__main__":
    # 调用并打印结果
    result = handle_function_call()
    print(result)
    print(result.response, result.action, result.result)

