import logging
import platform
import queue
import subprocess
import threading
import wave
import pyaudio
import json
from pydub import  AudioSegment
import pygame
import sounddevice as sd
import numpy as np
from playsound import playsound
from fastapi import FastAPI, WebSocket, WebSocketDisconnect


logger = logging.getLogger(__name__)


class AbstractPlayer(object):
    def __init__(self, *args, **kwargs):
        super(AbstractPlayer, self).__init__()
        self.is_playing = False
        self.play_queue = queue.Queue()
        self._stop_event = threading.Event()
        self.consumer_thread = threading.Thread(target=self._playing)
        self.consumer_thread.start()

    @staticmethod
    def to_wav(audio_file):
        tmp_file = audio_file + ".wav"
        wav_file = AudioSegment.from_file(audio_file)
        wav_file.export(tmp_file, format="wav")
        return tmp_file

    def _playing(self):
        while not self._stop_event.is_set():
            data = self.play_queue.get()
            self.is_playing = True
            try:
                self.do_playing(data)
            except Exception as e:
                logger.error(f"播放音频失败: {e}")
            finally:
                self.play_queue.task_done()
                self.is_playing = False

    def play(self, data):
        logger.info(f"play file {data}")
        audio_file = self.to_wav(data)
        self.play_queue.put(audio_file)

    def stop(self):
        self._clear_queue()

    def shutdown(self):
        self._clear_queue()
        self._stop_event.set()
        if self.consumer_thread.is_alive():
            self.consumer_thread.join()

    def get_playing_status(self):
        """正在播放和队列非空，为正在播放状态"""
        return self.is_playing or (not self.play_queue.empty())

    def _clear_queue(self):
        with self.play_queue.mutex:
            self.play_queue.queue.clear()

    def do_playing(self, audio_file):
        """播放音频的具体实现，由子类实现"""
        raise NotImplementedError("Subclasses must implement do_playing")


class CmdPlayer(AbstractPlayer):
    def __init__(self, *args, **kwargs):
        super(CmdPlayer, self).__init__(*args, **kwargs)
        self.p = pyaudio.PyAudio()

    def do_playing(self, audio_file):
        system = platform.system()
        cmd = ["afplay", audio_file] if system == "Darwin" else ["play", audio_file]
        logger.debug(f"Executing command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, shell=False, universal_newlines=True)
            logger.debug(f"播放完成：{audio_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"命令执行失败: {e}")
        except Exception as e:
            logger.error(f"未知错误: {e}")


class PyaudioPlayer(AbstractPlayer):
    def __init__(self, *args, **kwargs):
        super(PyaudioPlayer, self).__init__(*args, **kwargs)
        self.p = pyaudio.PyAudio()

    def do_playing(self, audio_file):
        chunk = 1024
        try:
            with wave.open(audio_file, 'rb') as wf:
                stream = self.p.open(format=self.p.get_format_from_width(wf.getsampwidth()),
                                     channels=wf.getnchannels(),
                                     rate=wf.getframerate(),
                                     output=True)
                data = wf.readframes(chunk)
                while data:
                    stream.write(data)
                    data = wf.readframes(chunk)
                stream.stop_stream()
                stream.close()
            logger.debug(f"播放完成：{audio_file}")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def stop(self):
        super().stop()
        if self.p:
            self.p.terminate()


class PygamePlayer(AbstractPlayer):
    def __init__(self, *args, **kwargs):
        super(PygamePlayer, self).__init__(*args, **kwargs)
        pygame.mixer.init()

    def do_playing(self, audio_file):
        try:
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(100)
            logger.debug("PygamePlayer 加载音频中")
            pygame.mixer.music.load(audio_file)
            logger.debug("PygamePlayer 加载音频结束，开始播放")
            pygame.mixer.music.play()
            logger.debug(f"播放完成：{audio_file}")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def get_playing_status(self):
        """正在播放和队列非空，为正在播放状态"""
        return self.is_playing or (not self.play_queue.empty()) or pygame.mixer.music.get_busy()

    def stop(self):
        super().stop()
        pygame.mixer.music.stop()

class PygameSoundPlayer(AbstractPlayer):
    """支持预加载"""
    def __init__(self, *args, **kwargs):
        super(PygameSoundPlayer, self).__init__(*args, **kwargs)
        pygame.mixer.init()

    def do_playing(self, current_sound):
        try:
            logger.debug("PygameSoundPlayer 播放音频中")
            current_sound.play()  # 播放音频
            while pygame.mixer.get_busy(): #current_sound.get_busy():  # 检查当前音频是否正在播放
                pygame.time.Clock().tick(100)  # 每秒检查100次
            del current_sound
            logger.debug(f"PygameSoundPlayer 播放完成")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def play(self, data):
        logger.info(f"play file {data}")
        audio_file = self.to_wav(data)
        sound = pygame.mixer.Sound(audio_file)
        self.play_queue.put(sound)

    def stop(self):
        super().stop()


class SoundDevicePlayer(AbstractPlayer):
    def do_playing(self, audio_file):
        try:
            wf = wave.open(audio_file, 'rb')
            data = wf.readframes(wf.getnframes())
            sd.play(np.frombuffer(data, dtype=np.int16), samplerate=wf.getframerate())
            sd.wait()
            logger.debug(f"播放完成：{audio_file}")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def stop(self):
        super().stop()
        sd.stop()


class PydubPlayer(AbstractPlayer):
    def do_playing(self, audio_file):
        try:
            audio = AudioSegment.from_file(audio_file)
            audio.play()
            logger.debug(f"播放完成：{audio_file}")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def stop(self):
        super().stop()
        # Pydub does not provide a stop method


class PlaysoundPlayer(AbstractPlayer):
    def do_playing(self, audio_file):
        try:
            playsound(audio_file)
            logger.debug(f"播放完成：{audio_file}")
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def stop(self):
        super().stop()
        # playsound does not provide a stop method


class WebSocketPlayer(AbstractPlayer):
    """通过WebSocket发送音频到前端"""

    def __init__(self, *args, **kwargs):
        super(WebSocketPlayer, self).__init__(*args, **kwargs)
        self.websocket = None
        self.playing_status = False

    def init(self, websocket: WebSocket):
        self.websocket = websocket

    def get_playing_status(self):
        """正在播放和队列非空，为正在播放状态"""
        return self.playing_status

    def set_playing_status(self, status):
        """正在播放和队列非空，为正在播放状态"""
        self.playing_status = status

    def do_playing(self, audio_file):
        try:
            with open(audio_file, "rb") as f:
                wav_data = f.read()
            self.websocket.send_bytes(wav_data)
        except Exception as e:
            logger.error(f"播放音频失败: {e}")

    def interrupt(self):
        """异步发送音频任务"""
        try:
            await self.websocket.send_text(json.dumps({"command": "interrupt"}))
        except Exception as e:
            logger.error(f"发送音频错误: {e}")

    def send_messages(self, messages):
        data = {
            "type": "update_dialogue",
            "dialogue": messages if isinstance(messages, list) else [messages]
        }
        try:
            await self.websocket.send_text(json.dumps(data))
        except Exception as e:
            logger.error(f"发送音频错误: {e}")

    def stop(self):
        """异步发送音频任务"""
        try:
            await self.websocket.send_text(json.dumps({"type": "interrupt"}))
        except Exception as e:
            logger.error(f"发送音频错误: {e}")


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        print(args,kwargs)
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")