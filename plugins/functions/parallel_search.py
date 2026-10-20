"""Web tools that return source excerpts to Bailing's normal LLM loop."""
import asyncio
import uuid
from urllib.parse import urlsplit

import httpx

from plugins import parallel_mcp
from plugins.registry import Action, ActionResponse, ToolType, register_function


def _run(name, arguments, session_id):
    arguments["session_id"] = session_id or str(uuid.uuid4())
    try:
        text = asyncio.run(parallel_mcp.call_tool(name, arguments))
    except (asyncio.TimeoutError, httpx.TimeoutException):
        text = "Parallel 请求超时，请稍后重试。"
    except httpx.HTTPStatusError as error:
        text = "Parallel 请求失败 (HTTP {})，请稍后重试。".format(error.response.status_code)
    except parallel_mcp.MCPError as error:
        text = "Parallel: " + str(error)
    except (httpx.RequestError, ValueError, TypeError, KeyError):
        text = "Parallel 搜索或网页读取失败，请稍后重试。"
    # TaskManager's WAIT path forwards response to Robot's tool message.
    return ActionResponse(Action.REQLLM, text, text)


@register_function("parallel_web_search", action=ToolType.WAIT)
def parallel_web_search(query, _session_id=None):
    if not isinstance(query, str) or not query.strip():
        text = "请提供非空的搜索关键词。"
        return ActionResponse(Action.REQLLM, text, text)
    return _run("web_search", {"objective": query, "search_queries": [query]}, _session_id)


@register_function("parallel_web_fetch", action=ToolType.WAIT)
def parallel_web_fetch(urls, _session_id=None):
    try:
        valid = isinstance(urls, list) and 1 <= len(urls) <= 20 and all(
            isinstance(url, str) and urlsplit(url).scheme in ("http", "https")
            and urlsplit(url).hostname and not urlsplit(url).username
            and not urlsplit(url).password for url in urls)
    except ValueError:
        valid = False
    if not valid:
        text = "请提供 1 至 20 个有效的 HTTP 或 HTTPS 网页地址。"
        return ActionResponse(Action.REQLLM, text, text)
    return _run("web_fetch", {"urls": urls}, _session_id)
