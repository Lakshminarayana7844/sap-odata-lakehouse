"""End-to-end: in-process mock server, full refresh, then incremental rerun."""
import pandas as pd
import requests

from ingest.client import ODataClient
from ingest.pipeline import LakehouseIngestor
from mock_odata.app import app
from mock_odata.data import ORDERS, PRODUCTS, SUPPLIERS
from fastapi.testclient import TestClient


def test_e2e_full_and_incremental(tmp_path, monkeypatch):
    tc = TestClient(app)
    monkeypatch.setattr(requests, "get", lambda url, timeout=10: tc.get(url[len("http://testserver"):]))
    client = ODataClient("http://testserver", page_size=25)
    ing = LakehouseIngestor(client, tmp_path)

    results = ing.run_all(full_refresh=True)
    counts = {r["entity_set"]: r["silver_rows"] for r in results}
    assert counts == {"Suppliers": len(SUPPLIERS), "Products": len(PRODUCTS), "Orders": len(ORDERS)}

    # second run with no new data: nothing fetched, silver unchanged
    results = ing.run_all()
    assert all(r["fetched"] == 0 for r in results)
    assert len(pd.read_parquet(tmp_path / "silver" / "Orders.parquet")) == len(ORDERS)
