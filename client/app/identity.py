from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
import uuid
from pathlib import Path

IDENTITY_VERSION = 1


def _identity_path() -> Path:
    override = os.environ.get("NETWORK_MONITOR_IDENTITY_FILE")
    if override:
        return Path(override).expanduser()

    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "server_based_network_monitor" / "client_identity.json"


def _make_identity() -> str:
    raw = f"{uuid.getnode()}|{socket.gethostname()}|{platform.system()}|{platform.machine()}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16].upper()
    return f"CLIENT-{digest}"


def get_client_id(configured_id: str | None = None) -> str:
    if configured_id:
        return configured_id

    path = _identity_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("version") == IDENTITY_VERSION:
                client_id = str(data.get("client_id", "")).strip()
                if 1 <= len(client_id) <= 128:
                    return client_id
    except (OSError, ValueError, TypeError):
        pass

    client_id = _make_identity()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps({"version": IDENTITY_VERSION, "client_id": client_id}, indent=2),
            encoding="utf-8",
        )
        temp_path.replace(path)
    except OSError:
        pass
    return client_id
