import os.path
import uuid
from typing import List, Dict
from datetime import datetime
from bailing.utils import write_json_file


class Message:
    def __init__(self, role: str, content: str = None, uniq_id: str = None, start_time: datetime = None, end_time: datetime = None,
                 audio_file: str = None, tts_file: str = None, vad_status: list = None, tool_calls = None, tool_call_id=None):
        self.uniq_id = uniq_id if uniq_id is not None else str(uuid.uuid4())
        self.role = role
        self.content = content
        self.start_time = start_time
        self.end_time = end_time
        self.audio_file = audio_file
        self.tts_file = tts_file
        self.vad_status = vad_status
        self.tool_calls = tool_calls
        self.tool_call_id = tool_call_id


class Dialogue:
    def __init__(self, dialogue_history_path):
        self.dialogue_history_path = dialogue_history_path
        self.dialogue: List[Message] = []
        # 获取当前时间
        self.current_time  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def put(self, message: Message):
        self.dialogue.append(message)

    def get_llm_dialogue(self) -> List[Dict[str, str]]:
        dialogue = []
        for m in self.dialogue:
            if m.tool_calls is not None:
                dialogue.append({"role": m.role, "tool_calls": m.tool_calls})
            elif m.role == "tool":
                dialogue.append({"role": m.role, "tool_call_id": m.tool_call_id, "content": m.content})
            else:
                dialogue.append({"role": m.role, "content": m.content})
        return dialogue

    def dump_dialogue(self):
        dialogue = []
        for d in self.get_llm_dialogue():
            if d["role"] not in ("user", "assistant"):
                continue
            dialogue.append(d)
        file_name = os.path.join(self.dialogue_history_path, f"dialogue-{self.current_time}.json")
        write_json_file(file_name, dialogue)

if __name__ == "__main__":
    d = Dialogue("../tmp/")
    d.put(Message(role="user", content="你好"))
    d.dump_dialogue()