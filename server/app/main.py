import asyncio
import json
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
DB_PATH = Path(os.getenv("NETWORK_MONITOR_DB", str(BASE_DIR / "data" / "network_monitor.db")))
STALE_SECONDS = float(os.getenv("NETWORK_MONITOR_STALE_SECONDS", "5"))
TOKEN = os.getenv("NETWORK_MONITOR_TOKEN", "")
MAX_COUNTER = (1 << 64) - 1

clients = {}
clients_lock = asyncio.Lock()


def db_connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    with db_connect() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS clients (
                client_id TEXT PRIMARY KEY,
                total_download_bytes INTEGER NOT NULL DEFAULT 0,
                total_upload_bytes INTEGER NOT NULL DEFAULT 0,
                public_ip TEXT NOT NULL DEFAULT '',
                last_seen REAL NOT NULL DEFAULT 0,
                last_rx_bytes INTEGER,
                last_tx_bytes INTEGER
            )
            """
        )
        columns = {row["name"] for row in db.execute("PRAGMA table_info(clients)")}
        if "last_rx_bytes" not in columns:
            db.execute("ALTER TABLE clients ADD COLUMN last_rx_bytes INTEGER")
        if "last_tx_bytes" not in columns:
            db.execute("ALTER TABLE clients ADD COLUMN last_tx_bytes INTEGER")
        db.commit()


def load_persisted_clients():
    with db_connect() as db:
        rows = db.execute("SELECT * FROM clients").fetchall()
    for row in rows:
        clients[row["client_id"]] = {
            "client_id": row["client_id"],
            "public_ip": row["public_ip"],
            "total_download_bytes": int(row["total_download_bytes"]),
            "total_upload_bytes": int(row["total_upload_bytes"]),
            "last_seen": float(row["last_seen"]),
            "last_rx_bytes": row["last_rx_bytes"],
            "last_tx_bytes": row["last_tx_bytes"],
            "download_bps": 0.0,
            "upload_bps": 0.0,
            "previous_rx": None,
            "previous_tx": None,
            "previous_time": None,
        }


def save_client(client):
    with db_connect() as db:
        db.execute(
            """
            INSERT INTO clients (
                client_id, total_download_bytes, total_upload_bytes,
                public_ip, last_seen, last_rx_bytes, last_tx_bytes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(client_id) DO UPDATE SET
                total_download_bytes=excluded.total_download_bytes,
                total_upload_bytes=excluded.total_upload_bytes,
                public_ip=excluded.public_ip,
                last_seen=excluded.last_seen,
                last_rx_bytes=excluded.last_rx_bytes,
                last_tx_bytes=excluded.last_tx_bytes
            """,
            (
                client["client_id"],
                client["total_download_bytes"],
                client["total_upload_bytes"],
                client["public_ip"],
                client["last_seen"],
                client["last_rx_bytes"],
                client["last_tx_bytes"],
            ),
        )
        db.commit()


async def snapshot():
    now = time.time()
    async with clients_lock:
        result = []
        for client in clients.values():
            online = now - client["last_seen"] <= STALE_SECONDS
            result.append(
                {
                    "client_id": client["client_id"],
                    "public_ip": client["public_ip"],
                    "download_bps": client["download_bps"] if online else 0.0,
                    "upload_bps": client["upload_bps"] if online else 0.0,
                    "total_download_bytes": client["total_download_bytes"],
                    "total_upload_bytes": client["total_upload_bytes"],
                    "total_traffic_bytes": client["total_download_bytes"] + client["total_upload_bytes"],
                    "online": online,
                    "last_seen": client["last_seen"],
                }
            )
        return {"timestamp": now, "clients": sorted(result, key=lambda item: item["client_id"].lower())}


class DashboardHub:
    def __init__(self):
        self.connections = set()

    async def add(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)

    def remove(self, websocket: WebSocket):
        self.connections.discard(websocket)

    async def broadcast(self, payload):
        message = json.dumps(payload, separators=(",", ":"))
        stale = []
        for connection in list(self.connections):
            try:
                await connection.send_text(message)
            except Exception:
                stale.append(connection)
        for connection in stale:
            self.remove(connection)


hub = DashboardHub()


async def cleanup_loop():
    while True:
        await hub.broadcast(await snapshot())
        await asyncio.sleep(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    load_persisted_clients()
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Server Based Network Monitor", lifespan=lifespan)


@app.get("/")
async def dashboard():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "clients": len(clients), "timestamp": time.time()}


@app.websocket("/ws/dashboard")
async def dashboard_socket(websocket: WebSocket):
    await hub.add(websocket)
    try:
        await websocket.send_text(json.dumps(await snapshot(), separators=(",", ":")))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.remove(websocket)
    except Exception:
        hub.remove(websocket)


@app.websocket("/ws/client")
async def client_socket(websocket: WebSocket):
    supplied_token = websocket.query_params.get("token", "")
    if TOKEN and supplied_token != TOKEN:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await websocket.accept()
    remote_ip = websocket.client.host if websocket.client else ""

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            if payload.get("type") != "heartbeat":
                continue

            client_id = str(payload.get("client_id", "")).strip()
            if not client_id or len(client_id) > 128:
                await websocket.close(code=1008, reason="Invalid client_id")
                return

            rx_bytes = int(payload.get("rx_bytes", 0))
            tx_bytes = int(payload.get("tx_bytes", 0))
            if not (0 <= rx_bytes <= MAX_COUNTER and 0 <= tx_bytes <= MAX_COUNTER):
                await websocket.close(code=1008, reason="Invalid counters")
                return

            now = time.time()
            async with clients_lock:
                client = clients.setdefault(
                    client_id,
                    {
                        "client_id": client_id,
                        "public_ip": remote_ip,
                        "total_download_bytes": 0,
                        "total_upload_bytes": 0,
                        "last_seen": now,
                        "last_rx_bytes": None,
                        "last_tx_bytes": None,
                        "download_bps": 0.0,
                        "upload_bps": 0.0,
                        "previous_rx": None,
                        "previous_tx": None,
                        "previous_time": None,
                    },
                )

                if client["previous_rx"] is not None and client["previous_time"] is not None:
                    elapsed = now - client["previous_time"]
                    if elapsed > 0 and rx_bytes >= client["previous_rx"] and tx_bytes >= client["previous_tx"]:
                        client["download_bps"] = (rx_bytes - client["previous_rx"]) * 8 / elapsed
                        client["upload_bps"] = (tx_bytes - client["previous_tx"]) * 8 / elapsed
                    else:
                        client["download_bps"] = 0.0
                        client["upload_bps"] = 0.0

                if client["last_rx_bytes"] is None:
                    client["total_download_bytes"] = max(client["total_download_bytes"], rx_bytes)
                elif rx_bytes >= client["last_rx_bytes"]:
                    client["total_download_bytes"] += rx_bytes - client["last_rx_bytes"]
                else:
                    # Counter reset/reboot: count the new counter value from zero.
                    client["total_download_bytes"] += rx_bytes

                if client["last_tx_bytes"] is None:
                    client["total_upload_bytes"] = max(client["total_upload_bytes"], tx_bytes)
                elif tx_bytes >= client["last_tx_bytes"]:
                    client["total_upload_bytes"] += tx_bytes - client["last_tx_bytes"]
                else:
                    # Counter reset/reboot: count the new counter value from zero.
                    client["total_upload_bytes"] += tx_bytes

                client["last_rx_bytes"] = rx_bytes
                client["last_tx_bytes"] = tx_bytes
                client["previous_rx"] = rx_bytes
                client["previous_tx"] = tx_bytes
                client["previous_time"] = now
                client["last_seen"] = now
                client["public_ip"] = remote_ip
                persisted_client = {
                    "client_id": client["client_id"],
                    "total_download_bytes": client["total_download_bytes"],
                    "total_upload_bytes": client["total_upload_bytes"],
                    "public_ip": client["public_ip"],
                    "last_seen": client["last_seen"],
                    "last_rx_bytes": client["last_rx_bytes"],
                    "last_tx_bytes": client["last_tx_bytes"],
                }

            await asyncio.to_thread(save_client, persisted_client)
            await hub.broadcast(await snapshot())
    except WebSocketDisconnect:
        return
    except (ValueError, TypeError, json.JSONDecodeError):
        await websocket.close(code=1003, reason="Invalid heartbeat")
    except Exception:
        await websocket.close(code=1011, reason="Server error")
