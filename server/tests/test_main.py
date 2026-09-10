import json

import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    main.DB_PATH = tmp_path / "network_monitor_test.db"
    main.clients.clear()
    yield
    main.clients.clear()


def test_health_endpoint():
    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["clients"] == 0


def test_client_heartbeat_and_dashboard_snapshot():
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws/client") as client_ws:
            client_ws.send_text(
                json.dumps(
                    {
                        "type": "heartbeat",
                        "client_id": "TEST-01",
                        "rx_bytes": 1000,
                        "tx_bytes": 2000,
                        "timestamp": 1760000000,
                    }
                )
            )

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


def test_invalid_counters_close_client_socket():
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws/client") as client_ws:
            client_ws.send_text(
                json.dumps(
                    {
                        "type": "heartbeat",
                        "client_id": "TEST-NEGATIVE",
                        "rx_bytes": -1,
                        "tx_bytes": 0,
                    }
                )
            )
            message = client_ws.receive()

    assert message["type"] == "websocket.close"
    assert message["code"] == 1008
