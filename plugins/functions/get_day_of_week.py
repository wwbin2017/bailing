from datetime import datetime
from plugins.registry import register_function
from plugins.registry import ActionResponse, Action
@register_function('get_day_of_week')
def get_day_of_week()->ActionResponse:
    # 获取当前日期和时间
    current_datetime = datetime.now()
    # 获取当前日期
    current_date = current_datetime.date()
    # 获取当前时间
    current_time = current_datetime.time()
    # 获取星期几（数字表示）
    weekday_number = current_datetime.weekday()
    # 中文星期几名称映射
    chinese_weekdays = {
        0: "星期一",
        1: "星期二",
        2: "星期三",
        3: "星期四",
        4: "星期五",
        5: "星期六",
        6: "星期日"
    }
    # 获取星期几的中文名称
    weekday_name = chinese_weekdays[weekday_number]
    response =  f"当前日期: {current_date}，当前时间: {current_time.strftime('%H:%M:%S')}，星期几: {weekday_name}"
    return ActionResponse(Action.REQLLM, None, response)

if __name__ == "__main__":
    print(get_day_of_week())
