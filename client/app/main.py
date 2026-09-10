from __future__ import annotations

import asyncio
import logging
import signal

from .config import parse_args
from .identity import get_client_id
from .websocket_client import MonitorClient


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def async_main() -> None:
    config = parse_args()
    configure_logging(config.log_level)
    logger = logging.getLogger(__name__)
    client_id = get_client_id(config.client_id)
    logger.info("Client ID: %s", client_id)

    client = MonitorClient(
        server_url=config.server_url,
        client_id=client_id,
        token=config.token,
        interval=config.interval,
        reconnect_delay=config.reconnect_delay,
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, client.stop)
        except (NotImplementedError, RuntimeError):
            pass

    await client.run()


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
