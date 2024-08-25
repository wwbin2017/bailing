import uuid
from typing import List, Dict
from datetime import datetime


class Message:
    def __init__(self, role: str, content: str, uniq_id: str = None, start_time: datetime = None, end_time: datetime = None,
                 audio_file: str = None, tts_file: str = None, vad_status: list = None):
        self.uniq_id = uniq_id if uniq_id is not None else str(uuid.uuid4())
        self.role = role
        self.content = content
        self.start_time = start_time
        self.end_time = end_time
        self.audio_file = audio_file
        self.tts_file = tts_file
        self.vad_status = vad_status


class Dialogue:
    def __init__(self):
        self.dialogue: List[Message] = []

    def put(self, message: Message):
        self.dialogue.append(message)

    def get_llm_dialogue(self) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.dialogue]
