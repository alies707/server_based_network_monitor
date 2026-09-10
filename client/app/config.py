from __future__ import annotations

import argparse
import os
from dataclasses import dataclass


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

    if not args.server.startswith(("ws://", "wss://")):
        parser.error("--server must start with ws:// or wss://")
    if args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if args.reconnect_delay <= 0:
        parser.error("--reconnect-delay must be greater than zero")

    return ClientConfig(
        server_url=args.server,
        client_id=args.client_id.strip() if args.client_id else None,
        token=args.token,
        interval=args.interval,
        reconnect_delay=args.reconnect_delay,
        log_level=args.log_level.upper(),
    )
