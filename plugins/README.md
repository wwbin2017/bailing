# 百聆插件

欢迎使用百聆插件的 function call 支持功能！本文档将指导你如何配置和使用这一功能。


## 简介

百聆（Bailing）是一个开源的语音助手，旨在通过集成 ASR、LLM 和 TTS 技术提供类似 GPT-4o 的性能。这个插件现在支持 function call 能力，可以让你通过函数调用扩展其功能。

## 功能

- **动态功能调用**：通过定义函数接口，实现动态调用功能。
- **灵活配置**：支持多种功能配置方式。


## 配置

1. **创建配置文件**：在项目根目录下创建一个名为 `function_calls_config.json` 的配置文件。该文件将用于定义你的 function call 相关配置。

    ```json
   {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取某个地点的天气，用户应先提供一个位置，比如用户说杭州天气，参数为：zhejiang/hangzhou，比如用户说北京天气怎么样，参数为：beijing/beijing",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市，zhejiang/hangzhou"
                    }
                },
                "required": [
                    "city"
                ]
            }
        }
    }
    ```
   
2. **实现函数逻辑**：在functions文件夹下，实现你的工具逻辑

```python
import requests
from bs4 import BeautifulSoup

from plugins.registry import register_function
from plugins.registry import ActionResponse, Action

@register_function('get_weather')
def get_weather(city: str):
    """
    "获取某个地点的天气，用户应先提供一个位置，\n比如用户说杭州天气，参数为：zhejiang/hangzhou，\n\n比如用户说北京天气怎么样，参数为：beijing/beijing",
    city : 城市，zhejiang/hangzhou
    """
    url = "https://tianqi.moji.com/weather/china/"+city
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    if response.status_code!=200:
        return ActionResponse(Action.REQLLM, None, "请求失败")
    soup = BeautifulSoup(response.text, "html.parser")
    weather = soup.find('meta', attrs={'name':'description'})["content"]
    weather = weather.replace("墨迹天气", "")
    return ActionResponse(Action.REQLLM, None, weather)

if __name__ == "__main__":
    print(get_weather("zhejiang/hangzhou"))
 
```


3. 当前支持的工具有：

| 函数名                | 描述                                          | 功能                                                       | 示例                                                         |
|-----------------------|-----------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------|
| `get_weather`         | 获取某个地点的天气信息                        | 提供地点名称后，返回该地点的天气情况                       | 用户说：“杭州天气怎么样？” → `zhejiang/hangzhou`             |
| `ielts_speaking_practice` | IELTS（雅思）口语练习                     | 生成雅思口语练习题目和对话，帮助用户进行雅思口语练习       | -                                                            |
| `get_day_of_week`     | 获取当前的星期几或日期                        | 当用户询问当前时间、日期或者星期几时，返回相应的信息       | 用户说：“今天星期几？” → 返回当前的星期几                    |
| `schedule_task`       | 创建一个定时任务                              | 用户可以指定任务的执行时间和内容，定时提醒用户             | 用户说：“每天早上8点提醒我喝水。” → `time: '08:00', content: '提醒我喝水'` |
| `open_application`    | 在 Mac 电脑上打开指定的应用程序                | 用户可以指定应用程序的名称，脚本将在 Mac 上启动相应的应用 | 用户说：“打开Safari。” → `application_name: 'Safari'`        |
| `web_search`          | 在网上搜索指定的关键词                        | 根据用户提供的搜索内容，返回相应的搜索结果                 | 用户说：“搜索最新的科技新闻。” → `query: '最新的科技新闻'`    |

