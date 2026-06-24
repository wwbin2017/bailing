import asyncio
import logging
import os
import subprocess
import time
import uuid
from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
from gtts import gTTS
import edge_tts
import requests
import ChatTTS
import torch
import torchaudio
import soundfile as sf
from kokoro import KModel, KPipeline

logger = logging.getLogger(__name__)


class AbstractTTS(ABC):
    __metaclass__ = ABCMeta

    @abstractmethod
    def to_tts(self, text):
        pass


class GTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file")
        self.lang = config.get("lang")

    def _generate_filename(self, extension=".aiff"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"执行时间: {execution_time:.2f} 秒")

    def to_tts(self, text):
        tmpfile = self._generate_filename(".aiff")
        try:
            start_time = time.time()
            tts = gTTS(text=text, lang=self.lang)
            tts.save(tmpfile)
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.debug(f"生成TTS文件失败: {e}")
            return None


class MacTTS(AbstractTTS):
    """
    macOS 系统自带的TTS
    voice: say -v ? 可以打印所有语音
    """

    def __init__(self, config):
        super().__init__()
        self.voice = config.get("voice")
        self.output_file = config.get("output_file")

    def _generate_filename(self, extension=".aiff"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"执行时间: {execution_time:.2f} 秒")

    def to_tts(self, phrase):
        logger.debug(f"正在转换的tts：{phrase}")
        tmpfile = self._generate_filename(".aiff")
        try:
            start_time = time.time()
            res = subprocess.run(
                ["say", "-v", self.voice, "-o", tmpfile, phrase],
                shell=False,
                universal_newlines=True,
            )
            self._log_execution_time(start_time)
            if res.returncode == 0:
                return tmpfile
            else:
                logger.info("TTS 生成失败")
                return None
        except Exception as e:
            logger.info(f"执行TTS失败: {e}")
            return None


class EdgeTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file", "tmp/")
        self.voice = config.get("voice")

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")

    async def text_to_speak(self, text, output_file):
        communicate = edge_tts.Communicate(text, voice=self.voice)  # Use your preferred voice
        await communicate.save(output_file)

    def to_tts(self, text):
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        try:
            asyncio.run(self.text_to_speak(text, tmpfile))
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.info(f"Failed to generate TTS file: {e}")
            return None


class CHATTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file", ".")
        self.chat = ChatTTS.Chat()
        self.chat.load(compile=False)  # Set to True for better performance
        self.rand_spk = self.chat.sample_random_speaker()

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")

    def to_tts(self, text):
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        try:
            params_infer_code = ChatTTS.Chat.InferCodeParams(
                spk_emb=self.rand_spk,  # add sampled speaker
                temperature=.3,  # using custom temperature
                top_P=0.7,  # top P decode
                top_K=20,  # top K decode
            )
            params_refine_text = ChatTTS.Chat.RefineTextParams(
                prompt='[oral_2][laugh_0][break_6]',
            )
            wavs = self.chat.infer(
                [text],
                params_refine_text=params_refine_text,
                params_infer_code=params_infer_code,
            )
            try:
                torchaudio.save(tmpfile, torch.from_numpy(wavs[0]).unsqueeze(0), 24000)
            except:
                torchaudio.save(tmpfile, torch.from_numpy(wavs[0]), 24000)
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.error(f"Failed to generate TTS file: {e}")
            return None



# class KOKOROTTS(AbstractTTS):
#     def __init__(self, config):
#         from kokoro import KPipeline
#         self.output_file = config.get("output_file", ".")
#         self.lang = config.get("lang", "z")
#         self.pipeline = KPipeline(lang_code=self.lang)  # <= make sure lang_code matches voice
#         self.voice = config.get("voice", "zm_yunyang")
#
#     def _generate_filename(self, extension=".wav"):
#         return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")
#
#     def _log_execution_time(self, start_time):
#         end_time = time.time()
#         execution_time = end_time - start_time
#         logger.debug(f"Execution Time: {execution_time:.2f} seconds")
#
#     def to_tts(self, text):
#         tmpfile = self._generate_filename(".wav")
#         start_time = time.time()
#         try:
#             generator = self.pipeline(
#                 text, voice=self.voice,  # <= change voice here
#                 speed=1, split_pattern=r'\n+'
#             )
#             for i, (gs, ps, audio) in enumerate(generator):
#                 logger.debug(f"KOKOROTTS: i: {i}, gs：{gs}, ps：{ps}")  # i => index
#                 sf.write(tmpfile, audio, 24000)  # save each audio file
#             self._log_execution_time(start_time)
#             return tmpfile
#         except Exception as e:
#             logger.error(f"Failed to generate TTS file: {e}")
#             return None


class KOKOROTTS(AbstractTTS):
    def __init__(self, config):
        """
        config keys:
          - repo_id: HuggingFace repo ID for Kokoro model (e.g. 'hexgrad/Kokoro-82M-v1.1-zh')
          - lang:      'z' for Chinese, 'a' for multilingual/IPA fallback
          - voice:     e.g. 'zf_001' or 'zm_010'
          - output_dir: directory to write wav files to
          - sample_rate: audio sample rate (default 24000)
          - zero_padding: number of zeros between segments (default 5000)
        """
        self.repo_id      = config.get("repo_id", "hexgrad/Kokoro-82M-v1.1-zh")
        self.output_dir   = config.get("output_dir", ".")
        self.lang         = config.get("lang", "z")
        self.voice        = config.get("voice", "zf_001")
        self.sample_rate  = config.get("sample_rate", 24000)

        # device selection
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        # load model if Chinese TTS
        self.model = None
        if self.lang == "z":
            self.model = KModel(repo_id=self.repo_id).to(self.device).eval()

        # set up pipelines
        self._setup_pipelines()

    def _setup_pipelines(self):
        # English/IPA fallback pipeline
        self.en_pipeline = KPipeline(
            lang_code="a", repo_id=self.repo_id, model=False
        )

        def en_callable(text):
            if text == "Kokoro":
                return "kˈOkəɹO"
            elif text == "Sol":
                return "sˈOl"
            return next(self.en_pipeline(text)).phonemes

        self.en_callable = en_callable

        # Main TTS pipeline
        self.pipeline = KPipeline(
            lang_code=self.lang,
            repo_id=self.repo_id,
            model=self.model,
            en_callable=self.en_callable
        )

    def _generate_filename(self, extension=".wav"):
        fname = f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}"
        return os.path.join(self.output_dir, fname)

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")
    @staticmethod
    def _speed_callable(len_ps: int) -> float:
        """
        piecewise linear function to slow down generation for long inputs
        """
        speed = 0.8
        if len_ps <= 83:
            speed = 1.0
        elif len_ps < 183:
            speed = 1.0 - (len_ps - 83) / 500.0
        return speed * 1.1

    def to_tts(self, text: str) -> str:
        """
        Generate TTS for `text`. Returns path to the combined WAV file.
        """
        output_file = self._generate_filename(".wav")
        start_time = time.time()

        try:
            generator = self.pipeline(
                text.replace("\n", " "),
                voice=self.voice,
                speed=self._speed_callable,
                #split_pattern=r"\n+"
            )
            result = next(generator)
            wav = result.audio
            sf.write(output_file, wav, self.sample_rate)

            self._log_execution_time(start_time)
            return output_file
        except Exception as e:
            logger.error(f"[KOKOROTTS] Failed to generate TTS: {e}")
            return ""


class MiniMaxTTS(AbstractTTS):
    """MiniMax Text-to-Speech provider (T2A v2 HTTP API).

    Converts text to speech via MiniMax's cloud TTS service and writes the
    resulting audio to a local file. The API returns hex-encoded audio (not
    base64). Docs: https://platform.minimax.io/docs/api-reference/speech-t2a-http

    config keys:
      - api_key:     MiniMax API key (shared with the Chat API)
      - voice:       voice id, e.g. 'English_Graceful_Lady' (default)
      - model:       TTS model id, e.g. 'speech-2.8-hd' (default)
      - base_url:    API base url, default 'https://api.minimax.io'
      - output_file: directory to write audio files to
      - format:      audio format, default 'mp3'
      - sample_rate / bitrate / speed / vol / pitch: optional fine tuning
    """

    def __init__(self, config):
        self.output_file = config.get("output_file", "tmp/")
        self.api_key = config.get("api_key")
        self.voice = config.get("voice", "English_Graceful_Lady")
        self.model = config.get("model", "speech-2.8-hd")
        self.base_url = config.get("base_url", "https://api.minimax.io").rstrip("/")
        self.format = config.get("format", "mp3")
        self.sample_rate = config.get("sample_rate", 32000)
        self.bitrate = config.get("bitrate", 128000)
        self.speed = config.get("speed", 1)
        self.vol = config.get("vol", 1)
        self.pitch = config.get("pitch", 0)

    def _generate_filename(self, extension=".mp3"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")

    def to_tts(self, text):
        tmpfile = self._generate_filename(f".{self.format}")
        start_time = time.time()
        payload = {
            "model": self.model,
            "text": text,
            "stream": False,
            "voice_setting": {
                "voice_id": self.voice,
                "speed": self.speed,
                "vol": self.vol,
                "pitch": self.pitch,
            },
            "audio_setting": {
                "sample_rate": self.sample_rate,
                "bitrate": self.bitrate,
                "format": self.format,
                "channel": 1,
            },
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                f"{self.base_url}/v1/t2a_v2", headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()
            result = response.json()
            base_resp = result.get("base_resp", {})
            if base_resp.get("status_code") != 0:
                logger.error(f"MiniMax TTS failed: {base_resp.get('status_msg')}")
                return None
            audio_hex = result.get("data", {}).get("audio")
            if not audio_hex:
                logger.error("MiniMax TTS returned empty audio")
                return None
            with open(tmpfile, "wb") as f:
                f.write(bytes.fromhex(audio_hex))  # MiniMax returns hex, not base64
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.error(f"Failed to generate TTS file: {e}")
            return None


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")
