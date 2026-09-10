# Server Based Network Monitor

A Python-only Client/Server network monitoring system for live bandwidth and traffic monitoring.

**فارسی:** [راهنمای فارسی](README.fa.md)

## Features

- Live download and upload rate per client
- Human-readable rates: bps, Kbps, Mbps and Gbps
- Public/source IP observed by the server
- Total download, upload and combined traffic per client
- Online/offline detection
- RTL Persian web dashboard
- Live browser updates through WebSocket
- SQLite persistence for cumulative traffic
- Automatic client reconnect
- Stable client identity without manually assigning an ID
- Windows, Linux and macOS client support through `psutil`
- Input and counter validation
- Python 3.11, 3.12 and 3.13 CI coverage
- Monitoring-only by design: no remote command execution

## Architecture

```text
┌─────────────────────┐
│    Python Client    │
│                     │
│  Network Counters   │
│      RX / TX        │
└──────────┬──────────┘
           │ WebSocket
           ▼
┌─────────────────────┐
│   Python FastAPI    │
│       Server        │
│                     │
│ Live Rate           │
│ Public IP           │
│ Client Status       │
│ SQLite Persistence  │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
  SQLite     Dashboard
```

The client reports cumulative RX/TX byte counters. The server calculates live rates from counter deltas and stores cumulative traffic in SQLite. The server records the source address of the WebSocket connection as the client's observed source/public IP.

## Requirements

- Python 3.11+
- Network connectivity between clients and the server
- TLS/WSS recommended for production

## Repository Structure

```text
server_based_network_monitor/
├── client/
│   ├── app/
│   │   ├── config.py
│   │   ├── identity.py
│   │   ├── main.py
│   │   ├── network.py
│   │   └── websocket_client.py
│   ├── tests/
│   ├── requirements.txt
│   └── config.example.json
├── server/
│   ├── app/
│   ├── tests/
│   └── requirements.txt
├── .github/
│   └── workflows/
│       └── ci.yml
├── README.md
└── README.fa.md
```

## Server Installation

### Linux / macOS

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Windows PowerShell

```powershell
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH="."
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://SERVER_IP:8000/
```

Example:

```text
http://192.168.1.100:8000/
```

## Client Installation

### Linux / macOS

```bash
cd client
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.main --server ws://192.168.1.100:8000/ws/client
```

### Windows PowerShell

```powershell
cd client
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.main --server ws://192.168.1.100:8000/ws/client
```

Replace `192.168.1.100` with the actual server IP.

## Authentication

Set a shared token on the server:

```text
NETWORK_MONITOR_TOKEN=YOUR_STRONG_TOKEN
```

Run the client with the same token:

```bash
python -m app.main --server ws://192.168.1.100:8000/ws/client --token YOUR_STRONG_TOKEN
```

If the server token is unset, authentication is disabled for development.

## Configuration

Client command-line options:

```text
--server SERVER_URL
--client-id CLIENT_ID
--token TOKEN
--interval SECONDS
--reconnect-delay SECONDS
--log-level LEVEL
```

Environment variables:

```text
NETWORK_MONITOR_SERVER
NETWORK_MONITOR_CLIENT_ID
NETWORK_MONITOR_TOKEN
NETWORK_MONITOR_INTERVAL
NETWORK_MONITOR_RECONNECT_DELAY
NETWORK_MONITOR_LOG_LEVEL
NETWORK_MONITOR_IDENTITY_FILE
```

When no client ID is supplied, the client creates and persists a stable identity. `NETWORK_MONITOR_IDENTITY_FILE` can override the identity-file location.

## Protocol

Client heartbeat example:

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

The server uses its own receive time for rate calculations, so differences between client and server clocks do not affect live bandwidth measurements.

## Counter Reset Handling

If a new RX/TX counter is lower than the previous counter, the server treats this as a counter reset or system reboot and adds the new counter value instead of generating a negative delta.

## Public IP

The server records the source address of the WebSocket connection. If the server is behind a reverse proxy, trusted proxy handling must be configured before forwarded headers are used to identify the client IP.

## Testing

Run server tests:

```bash
PYTHONPATH=server python -m pytest -q server/tests
```

Run client tests:

```bash
python -m pytest -q client/tests
```

Run a syntax/compile check:

```bash
python -m compileall -q client/app server/app
```

GitHub Actions runs the server tests and the client test suite. The client is tested on Python 3.11, 3.12 and 3.13.

## Quick End-to-End Test

1. Start the server.
2. Open `http://SERVER_IP:8000/` in a browser.
3. Start one Python client.
4. Confirm that the client becomes Online.
5. Download a large file from the client and verify the Download rate.
6. Upload a large file and verify the Upload rate.
7. Stop the client and verify Offline detection.
8. Start the client again and verify that cumulative traffic remains stored.

## Security and Production Notes

- Use `wss://` with TLS in production.
- Set a strong authentication token.
- Do not expose the server directly to the Internet without appropriate firewall and reverse-proxy controls.
- Configure trusted proxy handling when using a reverse proxy.
- The current token transport uses a query parameter for compatibility with the existing protocol. A future hardened deployment should move authentication into the WebSocket handshake/header or an authenticated first message.
- The current release is monitoring-only and intentionally does not execute remote commands or modify client network configuration.

## License

No license has been selected yet. Add an appropriate open-source or proprietary license before distributing the project.
