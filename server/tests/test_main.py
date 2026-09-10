import json
import time

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    main.DB_PATH = tmp_path / "network_monitor_test.db"
    main.clients.clear()
    yield
    main.clients.clear()


def send_heartbeat(client_ws, client_id, rx_bytes, tx_bytes):
    client_ws.send_text(
        json.dumps(
            {
                "type": "heartbeat",
                "client_id": client_id,
                "rx_bytes": rx_bytes,
                "tx_bytes": tx_bytes,
                "timestamp": 1760000000,
            }
        )
    )


def test_health_endpoint():
    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["clients"] == 0


def test_client_heartbeat_and_dashboard_snapshot():
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws/client") as client_ws:
            send_heartbeat(client_ws, "TEST-01", 1000, 2000)

        with client.websocket_connect("/ws/dashboard") as dashboard_ws:
            payload = dashboard_ws.receive_json()

    assert len(payload["clients"]) == 1
    monitored = payload["clients"][0]
    assert monitored["client_id"] == "TEST-01"
    assert monitored["total_download_bytes"] == 1000
    assert monitored["total_upload_bytes"] == 2000
    assert monitored["total_traffic_bytes"] == 3000
    assert monitored["online"] is True
    assert monitored["public_ip"]


def test_live_traffic_rate_is_calculated():
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws/client") as client_ws:
            send_heartbeat(client_ws, "RATE-01", 1_000, 2_000)
            time.sleep(0.02)
            send_heartbeat(client_ws, "RATE-01", 11_000, 7_000)

        with client.websocket_connect("/ws/dashboard") as dashboard_ws:
            payload = dashboard_ws.receive_json()

    monitored = payload["clients"][0]
    assert monitored["download_bps"] > 0
    assert monitored["upload_bps"] > 0


def test_cumulative_traffic_handles_counter_reset():
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws/client") as client_ws:
            send_heartbeat(client_ws, "RESET-01", 1000, 2000)
            send_heartbeat(client_ws, "RESET-01", 1500, 2500)
            send_heartbeat(client_ws, "RESET-01", 200, 300)
            send_heartbeat(client_ws, "RESET-01", 500, 700)

        with client.websocket_connect("/ws/dashboard") as dashboard_ws:
            payload = dashboard_ws.receive_json()

    monitored = payload["clients"][0]
    assert monitored["total_download_bytes"] == 1500 + 200 + 300
    assert monitored["total_upload_bytes"] == 2500 + 300 + 400


def test_invalid_counters_close_client_socket():
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws/client") as client_ws:
            send_heartbeat(client_ws, "TEST-NEGATIVE", -1, 0)
            message = client_ws.receive()

    assert message["type"] == "websocket.close"
    assert message["code"] == 1008
