import time
from fastapi import FastAPI, WebSocket, Query, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager
import asyncio
import argparse
import json
import logging
import socket
from typing import Dict
from concurrent.futures import ThreadPoolExecutor

from bailing import robot

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('tmp/bailing.log')]
)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument('--config_path', type=str, default="config/config.yaml", help="配置文件路径")
args = parser.parse_args()
config_path = args.config_path

TIMEOUT = 600  # 活跃超时（秒，当前为 10 分钟）
active_robots: Dict[str, list] = {}  # 格式：{ user_id: [robot, last_ts] }
lock = asyncio.Lock()
executor = ThreadPoolExecutor()

async def cleanup_task():
    while True:
        now = time.time()
        async with lock:
            for uid, (rb, ts) in list(active_robots.items()):
                if now - ts > TIMEOUT:
                    try:
                        rb.recorder.stop_recording()
                        rb.shutdown()
                        logger.info(f"{uid} 的 robot 已释放")
                    except Exception as e:
                        logger.warning(f"{uid} robot 释放异常: {e}")
                    active_robots.pop(uid, None)
        await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cleanup_task())
    yield
    task.cancel()
    await task

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/", StaticFiles(directory="static", html=True), name="static")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, user_id: str = Query(...)):
    await websocket.accept()
    logger.info(f"WebSocket connected: user_id={user_id}")

    async with lock:
        if user_id not in active_robots:
            rb = robot.Robot(config_path, websocket)
            asyncio.get_event_loop().run_in_executor(executor, rb.run)
            active_robots[user_id] = [rb, time.time()]
        else:
            rb = active_robots[user_id][0]

    try:
        while True:
            msg = await websocket.receive()
            if "bytes" in msg:
                rb.recorder.put_audio(msg["bytes"])
            elif "text" in msg:
                msg_js = json.loads(msg["text"])
                if msg_js.get("type") == "playback_status":
                    playing = (msg_js["status"] == "playing") or (msg_js["queue_size"] > 0)
                    rb.player.set_playing_status(playing)
                else:
                    logger.warning(f"未知消息: {msg_js}")
            async with lock:
                active_robots[user_id][1] = time.time()

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnect: {user_id}")
    except Exception as e:
        logger.error(f"错误 for {user_id}: {e}")
    finally:
        # 清理资源
        async with lock:
            #rb.recorder.stop_recording()
            #rb.shutdown()
            #active_robots.pop(user_id, None)
            pass
        await websocket.close()
        logger.info(f"连接关闭并清理：{user_id}")

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"127.0.0.1 (fallback), 获取错误: {e}"

if __name__ == "__main__":
    print(f"\n在局域网中访问: http://{get_lan_ip()}:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, ws_ping_interval=20, ws_ping_timeout=30)
