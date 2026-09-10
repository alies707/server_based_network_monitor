# Server Based Network Monitor

A lightweight client/server network monitor.

## Features

- Live download/upload rate per client
- Human-readable units (bps, Kbps, Mbps, Gbps)
- Public IP observed by the server
- Total download/upload/traffic per client
- Online/offline state
- Browser dashboard updated over WebSocket
- SQLite persistence for cumulative counters
- C++17 client agent for Windows and Linux
- Python FastAPI server

## Architecture

```text
C++ Client Agent -> WebSocket -> FastAPI Server -> SQLite
                                      |
                                      +-> Browser Dashboard
```

The client reports cumulative RX/TX byte counters. The server calculates the live rate from counter deltas. The server also records the public source IP of the WebSocket connection, so the client does not need a third-party IP service.

## Server

```bash
cd server
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://SERVER_IP:8000/` in a browser.

Optional environment variables:

- `NETWORK_MONITOR_TOKEN`: shared token required by clients. If unset, authentication is disabled for development.
- `NETWORK_MONITOR_DB`: SQLite database path. Defaults to `data/network_monitor.db`.
- `NETWORK_MONITOR_STALE_SECONDS`: seconds without a heartbeat before a client is offline. Defaults to `5`.

## Client

The client uses C++17 and CMake. It collects interface counters and sends a heartbeat every second.

```bash
cmake -S client -B client/build
cmake --build client/build --config Release
```

Run with:

```text
network-monitor-client ws://SERVER_IP:8000/ws/client CLIENT-01 TOKEN
```

On Linux, interface counters are read from `/sys/class/net/*/statistics`. On Windows, the implementation uses `GetIfTable2` from IP Helper API.

## Protocol

Client -> server:

```json
{
  "type": "heartbeat",
  "client_id": "CLIENT-01",
  "rx_bytes": 123456789,
  "tx_bytes": 4567890,
  "timestamp": 1760000000
}
```

Server -> browser:

```json
{
  "clients": [
    {
      "client_id": "CLIENT-01",
      "public_ip": "203.0.113.10",
      "download_bps": 12345678,
      "upload_bps": 1234567,
      "total_download_bytes": 123456789,
      "total_upload_bytes": 4567890,
      "total_traffic_bytes": 128024679,
      "online": true
    }
  ]
}
```

## Notes

The current release is monitoring-only. It deliberately does not execute remote commands or modify network configuration. That keeps the first version small, auditable, and much harder to accidentally turn into a distributed disaster.
