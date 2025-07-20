import time
from abc import ABC, abstractmethod
import threading
import queue
import logging
import pyaudio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class AbstractRecorder(ABC):
    @abstractmethod
    def start_recording(self, audio_queue: queue.Queue):
        pass

    @abstractmethod
    def stop_recording(self):
        pass


class RecorderPyAudio(AbstractRecorder):
    def __init__(self, config):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 512  # Buffer size
        self.py_audio = pyaudio.PyAudio()
        self.stream = None
        self.thread = None
        self.running = False

    def start_recording(self, audio_queue: queue.Queue):
        if self.running:
            raise RuntimeError("Stream already running")
        
        def stream_thread():
            try:
                self.stream = self.py_audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk
                )
                self.running = True
                while self.running:
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    audio_queue.put(data)
            except Exception as e:
                logger.error(f"Error in stream: {e}")
            finally:
                self.stop_recording()

        self.thread = threading.Thread(target=stream_thread)
        self.thread.start()

    def stop_recording(self):
        if not self.running:
            return
        
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self.py_audio:
            self.py_audio.terminate()

        if self.thread:
            self.thread.join()
            self.thread = None

    def __del__(self):
        # Ensure resources are cleaned up on object deletion
        self.stop_recording()



class WebSocketRecorder(AbstractRecorder):
    """通过WebSocket接收前端音频"""

    def __init__(self, config):
        self.running = True
        self.audio_queue = None

    def start_recording(self, audio_queue: queue.Queue):
        self.audio_queue = audio_queue

    def put_audio(self, data):
        if self.running:
            self.audio_queue.put(data)
        else:
            logger.info(f"当前已暂停录音: {self.running}")

    def stop_recording(self):
        self.running = False



def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")


if __name__ == "__main__":
    audio_queue = queue.Queue()
    recorderPyAudio = RecorderPyAudio()
    recorderPyAudio.start_recording()
    time.sleep(10)

