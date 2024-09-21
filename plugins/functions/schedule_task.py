import schedule
import threading
import time
from datetime import datetime
import logging

from plugins.registry import register_function
from plugins.registry import ActionResponse, Action



logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.tasks = {}

    def schedule_task(self, task_id, time_str, content):
        """创建一个定时任务"""
        schedule.every().day.at(time_str).do(self.trigger_task, task_id, content)
        self.tasks[task_id] = (time_str, content)
        logger.info(f"任务已创建: {task_id} - 在 {time_str} 执行 '{content}'")

    def trigger_task(self, task_id, content):
        """执行到时的任务逻辑"""
        logger.info(f"触发任务 {task_id}: {content} at {time.strftime('%H:%M:%S')}")

    def list_tasks(self):
        """列出所有已调度的任务"""
        for task_id, (time_str, content) in self.tasks.items():
            logger.info(f"当前调度的任务: {task_id}: 在 {time_str} 执行 '{content}'")

    def remove_task(self, task_id):
        """移除指定的任务"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"任务 {task_id} 已移除")
        else:
            logger.info(f"任务 {task_id} 不存在")

    def run_scheduler(self):
        """运行任务调度器"""
        while True:
            schedule.run_pending()
            time.sleep(1)


scheduler = TaskScheduler()
scheduler_thread = threading.Thread(target=scheduler.run_scheduler)
scheduler_thread.start()


@register_function('schedule_task')
def schedule_task(time_str, content):
    """
    创建一个定时任务。

    Args:
        time_str (str): 任务的执行时间，格式为 'HH:mm'，比如 '08:00'。
        content (str): 任务的内容，比如 '提醒我喝水'。
    """
    scheduler.schedule_task(content, time_str, content)
    return ActionResponse(Action.RESPONSE, None, "好的，已帮您创建好定时提醒任务，时间到了我会提醒您哦")

# 示例：使用 TaskScheduler 创建和管理任务
if __name__ == "__main__":

    # 创建一些任务
    scheduler.schedule_task("task1", "08:00", "提醒我喝水")
    scheduler.schedule_task("task2", "09:00", "提醒我吃早餐")

    # 列出当前所有任务
    scheduler.list_tasks()

    # 移除一个任务
    scheduler.remove_task("task1")

    # 列出当前所有任务
    scheduler.list_tasks()

    # 启动任务调度器在新线程中运行

    # 主线程可以执行其他任务
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("调度器停止。")


