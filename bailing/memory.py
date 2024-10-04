import json
import os
import glob
import logging
import re

import openai

from bailing.utils import read_json_file, write_json_file

logger = logging.getLogger(__name__)

memory_prompt_template = """
你是一个对话记录员，负责提取和记录用户与助手之间的对话信息。请根据以下内容生成最新、最完整的对话摘要，突出与用户相关的有用信息，并确保摘要不超过800个字。历史对话摘要包含了之前记录的对话摘要，涉及用户的需求、偏好和关键问题。最近一次对话历史是最近的对话记录，包含用户和助手之间的具体交流内容。

# 历史对话摘要
${dialogue_abstract}

# 最近一次对话历史
${dialogue_history}

# 输出要求
- 综合历史对话摘要和最近的对话历史，形成一个结构化的对话摘要，需要考虑用户对话风格。
- 确保提取的信息具有实际价值，并能帮助理解用户的需求和背景。
- 摘要应清晰、简洁，便于后续参考和分析。
- 输出对话摘要，用户对话偏好，用户对话风格，以及下次应该采取的对话策略
"""

class Memory:
    def __init__(self, config):
        file_path = config.get("dialogue_history_path")
        self.memory_file = config.get("memory_file")
        if os.path.isfile(self.memory_file):
            self.memory = read_json_file(self.memory_file)
        else:
            self.memory = {"history_memory_file":[], "memory":""}

        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        self.base_url = config.get("url")
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url)

        self.read_dialogues_in_order(file_path)

        write_json_file(self.memory_file, self.memory)


    def get_memory(self):
        return self.memory["memory"]

    def update_memory(self, file_name, dialogue_history):
        memory_prompt = memory_prompt_template.replace("${dialogue_abstract}", self.memory["memory"])\
            .replace("${dialogue_history}", dialogue_history).strip()
        new_memory = None
        try:
            responses = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role":"user", "content":memory_prompt}],
                stream=False
            )
            new_memory = responses.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in response generation: {e}")
        if new_memory is not None:
            self.memory["history_memory_file"].append(file_name)
            self.memory["memory"] = new_memory

    @staticmethod
    def extract_time_from_filename(filename):
        """从文件名中提取时间信息"""
        match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', filename)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def read_dialogue_file(file_path):
        """读取 JSON 对话文件并返回对话列表"""
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                dialogues = json.load(file)
                return dialogues
            except json.JSONDecodeError as e:
                logger.error(f"解析 JSON 时出错: {e}")
                return []

    @staticmethod
    def dialogues_history(dialogues):
        """打印对话内容"""
        dialogues_str = list()
        for dialogue in dialogues:
            role = dialogue.get('role', '未知角色')
            content = dialogue.get('content', '')
            logger.debug(f"{role}: {content}")
            dialogues_str.append(role +": " + content)
        return "\n".join(dialogues_str)

    def read_dialogues_in_order(self, directory):
        """读取指定目录下的所有对话文件，按时间顺序排列"""
        # 获取所有符合命名规则的文件路径
        pattern = os.path.join(directory, 'dialogue-*-*-*.json')
        files = glob.glob(pattern)

        # 按时间排序
        #files.sort(key=lambda x: x.split('-')[1:4])  # 根据时间部分进行排序
        files.sort(key=lambda x: self.extract_time_from_filename(os.path.basename(x)))

        # 读取并打印所有对话
        for file_path in files:
            if file_path in self.memory["history_memory_file"]:
                logger.info(f"{file_path} 对话历史已经形成memory")
                continue
            logger.info(f"正在处理: {file_path}")
            dialogues = self.read_dialogue_file(file_path)
            dialogue_history = self.dialogues_history(dialogues)
            self.update_memory(file_path, dialogue_history)
