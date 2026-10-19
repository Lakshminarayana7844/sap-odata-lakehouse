import pytest

from ingest.client import ODataClient
from mock_odata.app import app
from mock_odata.data import PRODUCTS
from fastapi.testclient import TestClient


class ServerTransport:
    """Serve the FastAPI app in-process so tests need no network."""

    def __init__(self):
        self.tc = TestClient(app)

    def get(self, url, timeout=10):
        assert url.startswith("http://testserver")
        return self.tc.get(url[len("http://testserver"):])


def test_pagination_collects_all_rows(monkeypatch):
    import requests

    ts = ServerTransport()
    monkeypatch.setattr(requests, "get", ts.get)
    client = ODataClient("http://testserver", page_size=17)
    rows = list(client.iter_rows("Products"))
    assert len(rows) == len(PRODUCTS)
    assert {r["ProductID"] for r in rows} == {p["ProductID"] for p in PRODUCTS}


def test_incremental_filter(monkeypatch):
    import requests

    ts = ServerTransport()
    monkeypatch.setattr(requests, "get", ts.get)
    client = ODataClient("http://testserver", page_size=100)
    marker = sorted(p["LastModified"] for p in PRODUCTS)[40]
    rows = list(client.iter_rows("Products", f"LastModified gt datetime'{marker}'"))
    assert rows
    assert all(r["LastModified"] > marker for r in rows)
