import base64
import importlib

from fastapi.testclient import TestClient


def client(monkeypatch, tmp_path, password=None):
    monkeypatch.setenv("CACHE_PATH", str(tmp_path / "c.sqlite3"))
    monkeypatch.delenv("SERPAPI_KEY", raising=False)
    if password:
        monkeypatch.setenv("APP_PASSWORD", password)
    else:
        monkeypatch.delenv("APP_PASSWORD", raising=False)
    import app.main as main
    return TestClient(importlib.reload(main).app)


def test_open_without_password(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path)
    assert c.get("/api/status").status_code == 200
    assert c.get("/api/airports", params={"q": "gene"}).json()[0]["code"] == "GVA"
    assert c.get("/api/cash/all", params={"origin": "DXB", "destination": "GVA", "date": "2026-11-20"}).status_code == 503


def test_password_gate(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path, password="s3cret")
    assert c.get("/api/status").status_code == 401
    assert c.get("/healthz").status_code == 200
    bad = {"Authorization": "Basic " + base64.b64encode(b"me:wrong").decode()}
    good = {"Authorization": "Basic " + base64.b64encode(b"me:s3cret").decode()}
    assert c.get("/api/status", headers=bad).status_code == 401
    assert c.get("/api/status", headers=good).status_code == 200
