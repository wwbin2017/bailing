import os
import uuid
import wave
from abc import ABC, abstractmethod
import logging
from datetime import datetime

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess


logger = logging.getLogger(__name__)


class ASR(ABC):
    @staticmethod
    def _save_audio_to_file(audio_data, file_path):
        """将音频数据保存为WAV文件"""
        try:
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b''.join(audio_data))
            logger.info(f"ASR识别文件录音保存到：{file_path}")
        except Exception as e:
            logger.error(f"保存音频文件时发生错误: {e}")
            raise

    @abstractmethod
    def recognizer(self, stream_in_audio):
        """处理输入音频流并返回识别的文本，子类必须实现"""
        pass


class FunASR(ASR):
    def __init__(self, config):
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")
        print(config)

        self.model = AutoModel(
            model=self.model_dir,
            vad_kwargs={"max_single_segment_time": 30000},
            disable_update=True,
            hub="hf"
            # device="cuda:0",  # 如果有GPU，可以解开这行并指定设备
        )

    def recognizer(self, stream_in_audio):
        try:
            tmpfile = os.path.join(self.output_dir, f"asr-{datetime.now().date()}@{uuid.uuid4().hex}.wav")
            self._save_audio_to_file(stream_in_audio, tmpfile)

            res = self.model.generate(
                input=tmpfile,
                cache={},
                language="auto",  # 语言选项: "zn", "en", "yue", "ja", "ko", "nospeech"
                use_itn=True,
                batch_size_s=60,
            )

            text = rich_transcription_postprocess(res[0]["text"])
            logger.info(f"识别文本: {text}")
            return text, tmpfile

        except Exception as e:
            logger.error(f"ASR识别过程中发生错误: {e}")
            return None, None


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")