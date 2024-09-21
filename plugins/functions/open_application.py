from plugins.registry import register_function
from plugins.registry import ActionResponse, Action
import subprocess
import logging

logger = logging.getLogger(__name__)

@register_function('open_application')
def open_application(app_name):
    """
    打开指定的 macOS 应用程序。

    Args:
        app_name (str): 应用程序的名称，如 'Google Chrome'、'Visual Studio Code' 等。
    """
    try:
        # 使用 subprocess 调用 open 命令打开应用程序
        subprocess.run(['open', '-a', app_name], check=True)
        logger.info(f"{app_name} 已成功启动！")
        response = "好的，正在帮你打开应用"
        return ActionResponse(Action.RESPONSE, None, response)
    except subprocess.CalledProcessError:
        logger.error(f"无法启动应用程序: {app_name}")
        response = "打开应用失败"
        return ActionResponse(Action.REQLLM, None, response)


