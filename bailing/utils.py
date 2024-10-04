import yaml
import json
import re


def load_prompt(prompt_path):
    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()
    return prompt.strip()


def read_json_file(file_path):
    """读取 JSON 文件并返回内容"""
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            print(f"解析 JSON 时出错: {e}")
            return None

def write_json_file(file_path, data):
    """将数据写入 JSON 文件"""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def read_config(config_path):
    with open(config_path, "r",encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


def is_segment(tokens):
    if tokens[-1] in (",", ".", "?", "，", "。", "？", "！", "!", ";", "；", ":", "："):
        return True
    else:
        return False

def is_interrupt(query: str):
    for interrupt_word in ("停一下", "听我说", "不要说了", "stop", "hold on", "excuse me"):
        if query.lower().find(interrupt_word)>=0:
            return True
    return False

def extract_json_from_string(input_string):
    """提取字符串中的 JSON 部分"""
    pattern = r'(\{.*\})'
    match = re.search(pattern, input_string)
    if match:
        return match.group(1)  # 返回提取的 JSON 字符串
    return None
