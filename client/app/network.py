from __future__ import annotations

import platform
import time
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class NetworkCounters:
    rx_bytes: int
    tx_bytes: int


VIRTUAL_PREFIXES = (
    "lo",
    "docker",
    "veth",
    "br-",
    "virbr",
    "tun",
    "tap",
    "vmnet",
    "vboxnet",
    "zt",
    "tailscale",
)


def _is_candidate(name: str, stats: psutil._common.snetio) -> bool:
    lower = name.lower()
    if lower.startswith(VIRTUAL_PREFIXES):
        return False
    if getattr(stats, "isup", False) is False:
        return False

    system = platform.system()
    if system == "Windows":
        virtual_markers = ("virtual", "loopback", "hyper-v", "vethernet", "vpn", "tunnel")
        return not any(marker in lower for marker in virtual_markers)
    return True


def read_network_counters() -> NetworkCounters:
    pernic = psutil.net_io_counters(pernic=True, nowrap=True)
    rx = 0
    tx = 0
    for name, counters in pernic.items():
        if _is_candidate(name, counters):
            rx += int(counters.bytes_recv)
            tx += int(counters.bytes_sent)
    return NetworkCounters(rx_bytes=rx, tx_bytes=tx)


def read_network_counters_with_retry(retries: int = 3) -> NetworkCounters:
    last = NetworkCounters()
    for _ in range(max(1, retries)):
        try:
            return read_network_counters()
        except (OSError, RuntimeError):
            last = NetworkCounters()
            time.sleep(0.1)
    return last
