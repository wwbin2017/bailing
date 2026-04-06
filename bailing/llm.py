from abc import ABC, abstractmethod
import openai
import requests
import json
import logging

logger = logging.getLogger(__name__)


class LLM(ABC):
    @abstractmethod
    def response(self, dialogue):
        pass


class OpenAILLM(LLM):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        self.base_url = config.get("url")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, dialogue):
        try:
            responses = self.client.chat.completions.create(  #) ChatCompletion.create(
                model=self.model_name,
                messages=dialogue,
                stream=True
            )
            for chunk in responses:
                yield chunk.choices[0].delta.content
                #yield chunk.choices[0].delta.get("content", "")
        except Exception as e:
            logger.error(f"Error in response generation: {e}")

    def response_call(self, dialogue, functions_call):
        try:
            responses = self.client.chat.completions.create(  #) ChatCompletion.create(
                model=self.model_name,
                messages=dialogue,
                stream=True,
                tools=functions_call
            )
            for chunk in responses:
                yield chunk.choices[0].delta.content, chunk.choices[0].delta.tool_calls
                #yield chunk.choices[0].delta.get("content", "")
        except Exception as e:
            logger.error(f"Error in response generation: {e}")


class OllamaLLM(LLM):
    def __init__(self, config):
        self.model_name = config.get("model_name", "qwen2.5")
        self.base_url = config.get("url", "http://localhost:11434/api/chat")

    def response(self, dialogue):
        payload = {
            "model": self.model_name,
            "messages": dialogue,
            "stream": True
        }
        try:
            resp = requests.post(self.base_url, json=payload, stream=True)
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line.decode())
                content = data.get("message", {}).get("content")
                if content:
                    yield content
        except Exception as e:
            logger.error(f"OllamaLLM stream error: {e}")

    def response_call(self, dialogue, tools):
        """
        支持流式工具调用：
        tools: list of tool definitions, e.g. [{"type":"function","function":{...}}, ...]
        """
        payload = {
            "model": self.model_name,
            "messages": dialogue,
            "stream": True,
            "tools": tools
        }
        try:
            resp = requests.post(self.base_url, json=payload, stream=True)
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line.decode())
                msg = data.get("message", {})
                content = msg.get("content")
                tool_calls = msg.get("tool_calls")
                yield content, tool_calls
        except Exception as e:
            logger.error(f"OllamaLLM tool-call error: {e}")


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")


if __name__ == "__main__":
    # 创建 DeepSeekLLM 的实例
    config = {"model_name":"deepseek-chat"
        ,"api_key":"your_api_key", "url":"https://api.deepseek.com"}

    deepseek = create_instance("OpenAILLM", config)

    dialogue = [{"role": "user", "content": "杭州天气怎么样"}]
    tools = [
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
    ]
    # 打印逐步生成的响应内容
    for chunk in deepseek.response_call(dialogue, functions_call=tools):
        print(chunk)