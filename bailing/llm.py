import json
import logging
from abc import ABC, abstractmethod
import requests

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
        # Remove OpenAI client initialization, use requests to call the Ollama API
        # self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

    def response(self, dialogue):
        try:
            url = f"{self.base_url}/api/generate"
            headers = {
                "Content-Type": "application/json",
            }
            data = {
                "model": self.model_name,
                "prompt": "\n".join([f"{msg['role']}: {msg['content']}" for msg in dialogue]),
                "stream": True
            }
            response = requests.post(url, headers=headers, json=data, stream=True)
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    chunk = line.decode('utf-8')
                    import json
                    try:
                        chunk_data = json.loads(chunk)
                        if 'response' in chunk_data:
                            yield chunk_data['response']
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON chunk: {chunk}")
                        continue
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}. Response content: {response.text}")
        except Exception as e:
            logger.error(f"Error in response generation: {e}")

    def response_call(self, dialogue, functions_call):
        # Currently, Ollama does not natively support function calls. This method is temporarily kept as is or adjusted accordingly.
        try:
            url = f"{self.base_url}/api/generate"
            headers = {
                "Content-Type": "application/json",
            }
            # Simply concatenate the dialogue content as a prompt
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in dialogue])
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": True
            }
            response = requests.post(url, headers=headers, json=data, stream=True)
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    chunk = line.decode('utf-8')
                    try:
                        chunk_data = json.loads(chunk)
                        if 'response' in chunk_data:
                            yield chunk_data['response'], None  # Function call part returns None
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode JSON chunk: {chunk}")
                        continue
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}. Response content: {response.text}")
        except Exception as e:
            logger.error(f"Error in response generation: {e}")


def create_instance(class_name, *args, **kwargs):
    # Get the class object
    cls = globals().get(class_name)
    if cls:
        # Create and return an instance
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")


if __name__ == "__main__":
    # Create an instance of DeepSeekLLM
    deepseek = create_instance("DeepSeekLLM", api_key="your_api_key", base_url="your_base_url")
    # Print the step - by - step generated response content
    dialogue = [{"role": "user", "content": "hello"}]

    # 打印逐步生成的响应内容
    for chunk in deepseek.response(dialogue):
        print(chunk)
