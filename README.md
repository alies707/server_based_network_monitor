# Server Based Network Monitor

A lightweight Python client/server network monitor.

## Features

- Python client agent for Windows, Linux, and macOS
- Live download/upload rate per client
- Human-readable units (bps, Kbps, Mbps, Gbps)
- Public IP observed by the server
- Total download/upload/traffic per client
- Online/offline state
- Browser dashboard updated over WebSocket
- SQLite persistence for cumulative counters
- Automatic client reconnect
- Persistent client identity
- Optional shared-token authentication
- Monitoring-only design with no remote command execution

## Architecture

```text
Python Client Agent -> WebSocket -> FastAPI Server -> SQLite
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

## Python Client

Requirements: Python 3.10+.

Install dependencies:

```bash
cd client
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Run against a server:

```bash
python -m app.main --server ws://SERVER_IP:8000/ws/client
```

With an explicit client ID and token:

```bash
python -m app.main --server ws://SERVER_IP:8000/ws/client --client-id PC-01 --token SECRET
```

The client ID is persistent when it is not explicitly supplied. The identity is stored in the user's application configuration directory. It can be overridden with `NETWORK_MONITOR_IDENTITY_FILE`.

Useful options:

```text
--server SERVER_URL
--client-id CLIENT_ID
--token TOKEN
--interval SECONDS
--reconnect-delay SECONDS
--log-level LEVEL
```

The client uses `psutil` to collect network interface counters. Loopback and common virtual/tunnel interfaces are excluded to reduce double counting. The server remains the source of truth for live rates and cumulative totals.

## Protocol

Client -> server:

```json
{
  "type": "heartbeat",
  "protocol_version": 1,
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

## Testing

Run server tests:

```bash
PYTHONPATH=server python -m pytest -q server/tests
```

Run client tests:

```bash
python -m pytest -q client/tests
```

The GitHub Actions workflow runs both test suites and compiles the Python client package.

## Counter reset behavior

If a client counter becomes smaller than its previous value, the server treats it as a counter reset/reboot and adds the new counter value to the persisted total. This prevents a Windows/Linux restart from destroying the cumulative traffic history.

## Security

For production use, prefer `wss://` behind TLS and configure `NETWORK_MONITOR_TOKEN`. The current token is passed as a URL query parameter for compatibility with the existing server endpoint; avoid exposing URLs containing tokens in logs.

## Scope

The current release is monitoring-only. It deliberately does not execute remote commands or modify network configuration. That keeps the first version small, auditable, and much harder to accidentally turn into a distributed disaster.
