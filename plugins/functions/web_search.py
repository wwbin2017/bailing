import requests
from bs4 import BeautifulSoup

from plugins.registry import register_function, ToolType
from plugins.registry import ActionResponse, Action


@register_function('web_search', action=ToolType.TIME_CONSUMING)
def web_search(query, engine="baidu"):
    """
    在指定的搜索引擎上进行搜索，并返回搜索结果页面的 HTML 内容。

    Args:
        query (str): 搜索关键词。
        engine (str): 指定的搜索引擎，默认为 'google'。可以选择 'baidu'。

    Returns:
        str: 搜索结果页面的 HTML 内容。
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }

    if engine == 'baidu':
        params = {"wd": query}
        url = 'https://www.baidu.com/s'
    else:  # 默认为 Google
        params = {"q": query}
        url = 'https://www.google.com/search'
    print(url)
    # 发送 GET 请求
    response = requests.get(url, params=params, headers=headers)

    # 检查请求是否成功
    if response.status_code == 200:
        return ActionResponse(Action.REQLLM, response.text, None)
    else:
        return ActionResponse(Action.REQLLM, "搜索失败", None)
