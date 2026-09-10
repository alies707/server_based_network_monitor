from __future__ import annotations

import asyncio
import json
import logging
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import websockets
from websockets.asyncio.client import connect
from websockets.exceptions import WebSocketException

from .network import NetworkCounters, read_network_counters_with_retry

logger = logging.getLogger(__name__)


class MonitorClient:
    def __init__(self, server_url: str, client_id: str, token: str, interval: float, reconnect_delay: float):
        self.server_url = server_url
        self.client_id = client_id
        self.token = token
        self.interval = interval
        self.reconnect_delay = reconnect_delay
        self._stop_event = asyncio.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def _build_url(self) -> str:
        if not self.token:
            return self.server_url
        parts = urlsplit(self.server_url)
        params = dict(parse_qsl(parts.query, keep_blank_values=True))
        params["token"] = self.token
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))

    @staticmethod
    def _payload(client_id: str, counters: NetworkCounters) -> str:
        return json.dumps(
            {
                "type": "heartbeat",
                "protocol_version": 1,
                "client_id": client_id,
                "timestamp": time.time(),
                "rx_bytes": counters.rx_bytes,
                "tx_bytes": counters.tx_bytes,
            },
            separators=(",", ":"),
        )

    async def _send_loop(self, websocket) -> None:
        while not self._stop_event.is_set():
            # psutil is synchronous. Run it in a worker thread so a slow OS
            # network-counter query cannot block the heartbeat/WebSocket loop.
            counters = await asyncio.to_thread(read_network_counters_with_retry)
            await websocket.send(self._payload(self.client_id, counters))
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                continue

    async def run(self) -> None:
        url = self._build_url()
        while not self._stop_event.is_set():
            try:
                logger.info("Connecting to %s as %s", url.split("?", 1)[0], self.client_id)
                async with connect(
                    url,
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=5,
                    max_size=1024 * 1024,
                ) as websocket:
                    logger.info("Connected")
                    await self._send_loop(websocket)
            except asyncio.CancelledError:
                raise
            except (OSError, WebSocketException, asyncio.TimeoutError) as exc:
                logger.warning("Connection lost: %s", exc)
            except Exception:
                logger.exception("Unexpected client error")

            if not self._stop_event.is_set():
                logger.info("Reconnecting in %.1f seconds", self.reconnect_delay)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=self.reconnect_delay)
                except asyncio.TimeoutError:
                    pass
