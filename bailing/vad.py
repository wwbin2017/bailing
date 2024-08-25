import os
import uuid
import wave
from abc import ABC, abstractmethod
import logging
from datetime import datetime

import numpy as np
import torch
from silero_vad import load_silero_vad, VADIterator

logger = logging.getLogger(__name__)


class VAD(ABC):
    @abstractmethod
    def is_vad(self, data):
        pass

    def reset_states(self):
        pass


class SileroVAD(VAD):
    def __init__(self, config):
        print("SileroVAD", config)
        self.model = load_silero_vad()
        self.sampling_rate = config.get("sampling_rate")
        self.threshold = config.get("threshold")
        self.min_silence_duration_ms = config.get("min_silence_duration_ms")
        self.vad_iterator = VADIterator(self.model,
                            threshold=self.threshold,
                            sampling_rate=self.sampling_rate,
                            min_silence_duration_ms=self.min_silence_duration_ms)
        logger.debug(f"VAD Iterator initialized with model {self.model}")

    @staticmethod
    def int2float(sound):
        """
        Convert int16 audio data to float32.
        """
        sound = sound.astype(np.float32) / 32768.0
        return sound

    def is_vad(self, data):
        try:
            audio_int16 = np.frombuffer(data, dtype=np.int16)
            audio_float32 = self.int2float(audio_int16)
            vad_output = self.vad_iterator(torch.from_numpy(audio_float32))
            if vad_output is not None:
                logger.debug(f"VAD output: {vad_output}")
            return vad_output
        except Exception as e:
            logger.error(f"Error in VAD processing: {e}")
            return None

    def reset_states(self):
        try:
            self.vad_iterator.reset_states()  # Reset model states after each audio
            logger.debug("VAD states reset.")
        except Exception as e:
            logger.error(f"Error resetting VAD states: {e}")


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")
