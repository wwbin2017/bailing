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