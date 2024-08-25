import yaml


def load_prompt(prompt_path):
    with open(prompt_path, "r") as file:
        prompt = file.read()
    return prompt.strip()


def read_config(config_path):
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config


def is_segment(tokens):
    if tokens[-1] in (",", ".", "?", "，", "。", "？", "！", "!", ";", "；", ":", "："):
        return True
    else:
        return False

def is_interrupt(query: str):
    for interrupt_word in ("停一下", "听我说", "不要说了", "stop", "hold on", "excuse me", ""):
        if query.lower().find(interrupt_word)>=0:
            return True
    return False
