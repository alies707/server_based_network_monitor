# Server Based Network Monitor

A Python-only client/server network monitoring system.

## Features

- Live download/upload rate per client
- Human-readable network rates (bps, Kbps, Mbps, Gbps)
- Public IP observed by the server
- Total download/upload/traffic per client
- Online/offline state
- Browser dashboard updated over WebSocket
- SQLite persistence for cumulative counters
- Automatic Python client reconnect
- Stable client identity without manually assigning an ID
- Windows, Linux and macOS client support through `psutil`
- Python 3.11, 3.12 and 3.13 CI coverage
- Monitoring-only design: no remote command execution

## Architecture

```text
Python Client Agent -> WebSocket -> FastAPI Server -> SQLite
                                      |
                                      +-> Browser Dashboard
```

The client reports cumulative RX/TX byte counters. The server calculates live rates from counter deltas and persists cumulative traffic. The server records the source IP of the WebSocket connection as the client's observed public/source IP.

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

```bash
cd client
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

Start the client:

```bash
python -m app.main --server ws://SERVER_IP:8000/ws/client
```

With authentication:

```bash
python -m app.main --server ws://SERVER_IP:8000/ws/client --token YOUR_TOKEN
```

Optional settings:

```text
--client-id ID
--interval 1
--reconnect-delay 3
--log-level INFO
```

The client stores its generated identity in the platform's application configuration directory. `NETWORK_MONITOR_IDENTITY_FILE` can override the identity file location. A manually supplied `--client-id` takes precedence.

## Configuration via environment variables

```text
NETWORK_MONITOR_SERVER
NETWORK_MONITOR_CLIENT_ID
NETWORK_MONITOR_TOKEN
NETWORK_MONITOR_INTERVAL
NETWORK_MONITOR_RECONNECT_DELAY
NETWORK_MONITOR_LOG_LEVEL
NETWORK_MONITOR_IDENTITY_FILE
```

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

The server uses its own receive time for live-rate calculations, so client clock differences do not affect bandwidth measurements.

If the current counter is lower than the previously stored counter, the server treats it as a counter reset/reboot and adds the new counter value rather than producing a negative delta.

## Testing

Server tests:

```bash
PYTHONPATH=server python -m pytest -q server/tests
```

Client tests:

```bash
python -m pytest -q client/tests
```

Compile check:

```bash
python -m compileall -q client/app server/app
```

GitHub Actions runs server tests and the Python client test suite on Python 3.11, 3.12 and 3.13.

## Security and production notes

- Use `wss://` behind TLS in production.
- Set `NETWORK_MONITOR_TOKEN` outside development.
- The current token transport uses a query parameter for compatibility with the existing server protocol. For high-security deployments, move authentication into the WebSocket handshake/header or an initial authenticated message.
- If the server is behind a reverse proxy, configure trusted proxy handling before treating forwarded headers as the client's public IP.
- The current release is monitoring-only and deliberately does not execute remote commands or modify network configuration.
