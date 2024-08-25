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
        "function_calls": {
            "example_function": {
                "description": "这是一个示例函数。",
                "parameters": {
                    "param1": "string",
                    "param2": "integer"
                }
            }
        }
    }
    ```
