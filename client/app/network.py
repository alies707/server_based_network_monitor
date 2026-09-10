from __future__ import annotations

import time
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class NetworkCounters:
    rx_bytes: int
    tx_bytes: int


def read_network_counters() -> NetworkCounters:
    """Return cumulative receive/transmit byte counters for the whole client.

    The previous implementation summed only interfaces that passed a heuristic
    virtual-interface filter. On Windows and on some virtualized/network-driver
    setups, that filter can reject the real adapter, causing both counters to
    remain zero even while traffic is flowing. psutil's aggregate counters are
    maintained by the OS and are a better source for a client-wide traffic
    monitor.
    """
    counters = psutil.net_io_counters(pernic=False, nowrap=True)
    if counters is None:
        return NetworkCounters(0, 0)
    return NetworkCounters(
        rx_bytes=max(0, int(counters.bytes_recv)),
        tx_bytes=max(0, int(counters.bytes_sent)),
    )


def read_network_counters_with_retry(retries: int = 3) -> NetworkCounters:
    last = NetworkCounters(0, 0)
    for _ in range(max(1, retries)):
        try:
            return read_network_counters()
        except (OSError, RuntimeError):
            last = NetworkCounters(0, 0)
            time.sleep(0.1)
    return last
