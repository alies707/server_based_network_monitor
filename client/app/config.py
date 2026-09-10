from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ClientConfig:
    server_url: str
    client_id: str | None
    token: str
    interval: float
    reconnect_delay: float
    log_level: str


def parse_args() -> ClientConfig:
    parser = argparse.ArgumentParser(description="Server Based Network Monitor Python Client")
    parser.add_argument("--server", default=os.getenv("NETWORK_MONITOR_SERVER", "ws://127.0.0.1:8000/ws/client"))
    parser.add_argument("--client-id", default=os.getenv("NETWORK_MONITOR_CLIENT_ID"))
    parser.add_argument("--token", default=os.getenv("NETWORK_MONITOR_TOKEN", ""))
    parser.add_argument("--interval", type=float, default=float(os.getenv("NETWORK_MONITOR_INTERVAL", "1")))
    parser.add_argument("--reconnect-delay", type=float, default=float(os.getenv("NETWORK_MONITOR_RECONNECT_DELAY", "3")))
    parser.add_argument("--log-level", default=os.getenv("NETWORK_MONITOR_LOG_LEVEL", "INFO"))
    args = parser.parse_args()

    parts = urlsplit(args.server)
    if parts.scheme not in {"ws", "wss"} or not parts.netloc:
        parser.error("--server must be a valid ws:// or wss:// URL")
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.reconnect_delay <= 0:
        parser.error("--reconnect-delay must be greater than zero")
    if args.client_id is not None:
        args.client_id = args.client_id.strip()
        if not args.client_id:
            parser.error("--client-id cannot be empty")
        if len(args.client_id) > 128:
            parser.error("--client-id must be 128 characters or fewer")

    return ClientConfig(
        server_url=args.server,
        client_id=args.client_id,
        token=args.token,
        interval=args.interval,
        reconnect_delay=args.reconnect_delay,
        log_level=args.log_level.upper(),
    )
