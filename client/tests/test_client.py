import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.identity import get_client_id
from app.network import NetworkCounters
from app.websocket_client import MonitorClient


def test_payload_contains_protocol_and_counters():
    payload = json.loads(MonitorClient._payload("PC-01", NetworkCounters(123, 456)))
    assert payload["type"] == "heartbeat"
    assert payload["protocol_version"] == 1
    assert payload["client_id"] == "PC-01"
    assert payload["rx_bytes"] == 123
    assert payload["tx_bytes"] == 456


def test_token_is_url_encoded():
    client = MonitorClient("ws://localhost:8000/ws/client?x=1", "PC-01", "a+b&c/d?e", 1, 3)
    url = client._build_url()
    assert "token=a%2Bb%26c%2Fd%3Fe" in url
    assert "x=1" in url


def test_configured_client_id_wins():
    assert get_client_id("MY-PC") == "MY-PC"


def test_persistent_identity(monkeypatch, tmp_path):
    identity_file = tmp_path / "identity.json"
    monkeypatch.setenv("NETWORK_MONITOR_IDENTITY_FILE", os.fspath(identity_file))
    first = get_client_id()
    second = get_client_id()
    assert first.startswith("CLIENT-")
    assert first == second
    assert identity_file.exists()
