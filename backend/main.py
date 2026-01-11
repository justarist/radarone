import asyncio
import os
import json
import threading
from typing import Dict, Any

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
from logger import logger
import asyncio
import db
import listener
import bot as bot_module

load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
WS_PATH = "/ws"
PG_LISTEN_CHANNEL = os.getenv("PG_NOTIFY_CHANNEL", "attack_updates")
POLL_FALLBACK_SEC = int(os.getenv("POLL_FALLBACK_SEC", 5))

app = FastAPI()
uvicorn_config = {
    "host": HOST,
    "port": PORT,
    "log_level": "info",
    "loop": "asyncio",
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.lock = asyncio.Lock()
        self.last_snapshot = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.add(websocket)
        logger.info(f"[WS] Client connected (total: {len(self.active_connections)})")

        if self.last_snapshot is not None:
            await websocket.send_text(json.dumps({
                "type": "snapshot",
                "data": self.last_snapshot
            }, ensure_ascii=False))

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(f"[WS] Client disconnected (total: {len(self.active_connections)})")

    async def broadcast(self, message: Dict[str, Any]):
        text = json.dumps(message, ensure_ascii=False)
        async with self.lock:
            conns = list(self.active_connections)
        for ws in conns:
            try:
                await ws.send_text(text)
            except Exception:
                logger.exception("[WS] Error sending to client, disconnecting")
                try:
                    await ws.close()
                except Exception:
                    pass
                await self.disconnect(ws)

ws_manager = ConnectionManager()

@app.get("/api/statuses")
async def api_statuses():
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT region, attack_type, status
            FROM (
                SELECT DISTINCT ON (region, attack_type) region, attack_type, status, id
                FROM attacks
                ORDER BY region, attack_type, id DESC
            ) x
        """)
    result: Dict[str, Dict[str, str]] = {}
    for r in rows:
        rg = r["region"]
        at = r["attack_type"]
        st = r["status"]
        if rg not in result:
            result[rg] = {}
        result[rg][at] = st
    return result

@app.websocket(WS_PATH + "/")
@app.websocket(WS_PATH)
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                snapshot = await get_current_snapshot()
                await websocket.send_text(json.dumps(snapshot, ensure_ascii=False))
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        logger.exception("[WS] Unexpected error")
        await ws_manager.disconnect(websocket)

async def get_current_snapshot() -> Dict[str, Dict[str, str]]:
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT region, attack_type, status
            FROM (
                SELECT DISTINCT ON (region, attack_type) region, attack_type, status, id
                FROM attacks
                ORDER BY region, attack_type, id DESC
            ) x
        """)
    result: Dict[str, Dict[str, str]] = {}
    for r in rows:
        rg = r["region"]
        at = r["attack_type"]
        st = r["status"]
        if rg not in result:
            result[rg] = {}
        result[rg][at] = st
    return result

async def pg_listen_and_forward():
    logger.info(f"[PG] Starting LISTEN on channel '{PG_LISTEN_CHANNEL}'")

    pool = await db.get_pool()
    conn = await pool.acquire()

    try:
        async def handle_notification(payload: str):
            try:
                data = json.loads(payload)
            except:
                logger.error("[PG] Invalid payload")
                return

            region = data.get("region")
            if not region:
                logger.error("[PG] No region in payload")
                return

            region_snapshot = await db.get_last_status(region=region)

            await ws_manager.broadcast({
                "type": "region_update",
                "data": region_snapshot
            })

        def _listener(conn_obj, pid, channel, payload):
            asyncio.create_task(handle_notification(payload))

        await conn.add_listener(PG_LISTEN_CHANNEL, _listener)
        logger.info(f"[PG] Listening on channel '{PG_LISTEN_CHANNEL}'")

        while True:
            await asyncio.sleep(3600)

    except asyncio.CancelledError:
        logger.info("[PG] Listener cancelled")

    finally:
        try:
            await conn.remove_listener(PG_LISTEN_CHANNEL, _listener)
        except:
            pass
        await pool.release(conn)

async def poll_and_broadcast(manager: ConnectionManager):
    snapshot = await get_current_snapshot()
    if snapshot != manager.last_snapshot:
        manager.last_snapshot = snapshot
        await manager.broadcast({"type": "snapshot", "data": snapshot})
        logger.debug("[POLL] Broadcasted new snapshot to clients")
    return snapshot

async def poll_and_broadcast_loop(interval: int = POLL_FALLBACK_SEC):
    while True:
        try:
            await poll_and_broadcast(ws_manager)
        except Exception:
            logger.exception("[POLL] Error while polling DB")
        await asyncio.sleep(interval)

def start_bot_in_thread():
    def _target():
        asyncio.set_event_loop(asyncio.new_event_loop())
        try:
            logger.info("[BOT THREAD] Starting bot.main() (blocking)...")
            bot_module.main()
        except Exception:
            logger.exception("[BOT THREAD] Bot crashed")

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    return t

async def start_services():
    snapshot = await get_current_snapshot()
    asyncio.create_task(ws_manager.broadcast({
        "type": "snapshot",
        "data": snapshot
    }))
    
    listener_task = asyncio.create_task(listener.listener_loop(poll_interval=10))
    pg_task = asyncio.create_task(pg_listen_and_forward())
    poll_task = asyncio.create_task(poll_and_broadcast_loop(POLL_FALLBACK_SEC))
    bot_thread = start_bot_in_thread()
    return [listener_task, pg_task, poll_task, bot_thread]

async def stop_services(tasks):
    logger.info("[MAIN] Cancelling tasks...")
    for t in tasks:
        if isinstance(t, threading.Thread):
            continue
        t.cancel()
    await asyncio.sleep(0.1)

async def async_main():
    tasks = await start_services()

    config = uvicorn.Config(app, **uvicorn_config)
    server = uvicorn.Server(config)

    server_task = asyncio.create_task(server.serve())

    try:
        await server_task
    except asyncio.CancelledError:
        logger.info("[MAIN] Server cancelled")
    finally:
        await stop_services(tasks)
        await server.shutdown()

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("[MAIN] Interrupted by user")

if __name__ == "__main__":
    main()
