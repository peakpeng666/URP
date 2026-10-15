"""Check an empty, isolated SQLite database and the loopback health API."""
import http.client
import json
from pathlib import Path
import threading
import uuid

from backend.server import make_server
from backend.store import Store

base = Path(__file__).resolve().parent
database = base / "runtime" / f"backend-smoke-{uuid.uuid4().hex}.sqlite3"
store = Store(database)
server = make_server(store, base / "runtime", 0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
try:
    def request(path):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            conn.request("GET", path)
            response = conn.getresponse()
            assert response.status == 200, response.status
            return json.loads(response.read())
        finally:
            conn.close()
    health = request("/api/health")
    assert health["status"] == "ok" and health["executes_experiments"] is False
    assert request("/api/experiments") == {"experiments": []}
    print(json.dumps({"status": "PASS", "health": health, "database": str(database), "historical_data_loaded": False}, indent=2))
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
