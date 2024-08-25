import logging
import platform
import queue
import subprocess
import threading
import wave
import pyaudio
from pydub import  AudioSegment

logger = logging.getLogger(__name__)


class AbstractPlayer(object):
    def __init__(self, *args, **kwargs):
        super(AbstractPlayer, self).__init__()
        self.is_playing = False
        self.play_queue = queue.Queue()
        self._stop_event = threading.Event()
        self.consumer_thread = threading.Thread(target=self._playing)
        self.consumer_thread.start()

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
        self.play_queue.put(data)

    def stop(self):
        self._clear_queue()

    def shutdown(self):
        self._clear_queue()
        self._stop_event.set()
        if self.consumer_thread.is_alive():
            self.consumer_thread.join()

    def is_playing(self):
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

    @staticmethod
    def to_wav(audio_file):
        tmp_file = audio_file + ".wav"
        wav_file = AudioSegment.from_file(audio_file)
        wav_file.export(tmp_file, format="wav")
        return wav_file

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


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        print(args,kwargs)
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")