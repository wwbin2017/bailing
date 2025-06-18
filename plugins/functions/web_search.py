import asyncio
import json
import logging
import random
import time
import warnings

import requests
from bs4 import BeautifulSoup
from cachetools import TTLCache
from duckduckgo_search import AsyncDDGS, DDGS

from plugins.registry import register_function, ToolType
from plugins.registry import ActionResponse, Action


from duckduckgo_search import DDGS

class BaseSearch:

    def __init__(self, topk: int = 3, black_list: list[str] = None):
        self.topk = topk
        self.black_list = black_list

    def _filter_results(self, results: list[tuple]) -> dict:
        filtered_results = {}
        count = 0
        for url, snippet, title in results:
            if all(domain not in url for domain in self.black_list) and not url.endswith('.pdf'):
                filtered_results[count] = {
                    'url': url,
                    'summ': json.dumps(snippet, ensure_ascii=False)[1:-1],
                    'title': title,
                }
                count += 1
                if count >= self.topk:
                    break
        return filtered_results

class DuckDuckGoSearch(BaseSearch):

    def __init__(
        self,
        topk: int = 3,
        black_list: list[str] = [
            'enoN',
            'youtube.com',
            'bilibili.com',
            'researchgate.net',
        ],
        **kwargs,
    ):
        self.proxy = kwargs.get('proxy')
        self.timeout = kwargs.get('timeout', 3000)
        super().__init__(topk, black_list)

    def search(self, query: str, max_retry: int = 3) -> dict:
        for attempt in range(max_retry):
            try:
                response = self._call_ddgs(query, timeout=self.timeout, proxy=self.proxy)
                return self._parse_response(response)
            except Exception as e:
                logging.exception(str(e))
                warnings.warn(f'Retry {attempt + 1}/{max_retry} due to error: {e}')
                time.sleep(random.randint(2, 5))
        raise Exception('Failed to get search results from DuckDuckGo after retries.')

    async def asearch(self, query: str, max_retry: int = 3) -> dict:
        for attempt in range(max_retry):
            try:
                ddgs = AsyncDDGS(timeout=self.timeout, proxy=self.proxy)
                response = await ddgs.text(query.strip("'"), max_results=10)
                return self._parse_response(response)
            except Exception as e:
                if isinstance(e, asyncio.TimeoutError):
                    logging.exception('Request to DDGS timed out.')
                logging.exception(str(e))
                warnings.warn(f'Retry {attempt + 1}/{max_retry} due to error: {e}')
                await asyncio.sleep(random.randint(2, 5))
        raise Exception('Failed to get search results from DuckDuckGo after retries.')

    async def _async_call_ddgs(self, query: str, **kwargs) -> dict:
        ddgs = DDGS(**kwargs)
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(ddgs.text, query.strip("'"), max_results=10), timeout=self.timeout
            )
            return response
        except asyncio.TimeoutError:
            logging.exception('Request to DDGS timed out.')
            raise

    def _call_ddgs(self, query: str, **kwargs) -> dict:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(self._async_call_ddgs(query, **kwargs))
            return response
        finally:
            loop.close()

    def _parse_response(self, response: list[dict]) -> dict:
        raw_results = []
        for item in response:
            raw_results.append(
                (item['href'], item['description'] if 'description' in item else item['body'], item['title'])
            )
        return self._filter_results(raw_results)


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
