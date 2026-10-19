import pandas as pd
import pytest

from ingest.pipeline import LakehouseIngestor
from ingest.schemas import validate_rows


class FakeClient:
    def __init__(self, batches):
        self.batches = batches
        self.filters = []

    def iter_rows(self, entity_set, filter_expr=None):
        self.filters.append(filter_expr)
        yield from self.batches[entity_set]


SUPPLIERS = [
    {"SupplierID": 1, "CompanyName": "Acme", "Country": "DE", "LastModified": "2026-08-01T09:00:00Z"},
    {"SupplierID": 2, "CompanyName": "Bolt", "Country": "NL", "LastModified": "2026-08-01T10:00:00Z"},
]


def test_full_then_incremental_upserts(tmp_path):
    client = FakeClient({"Suppliers": SUPPLIERS})
    ing = LakehouseIngestor(client, tmp_path)
    result = ing.run_entity("Suppliers")
    assert result["fetched"] == 2 and result["silver_rows"] == 2

    changed = [dict(SUPPLIERS[0], CompanyName="Acme Renamed", LastModified="2026-08-02T09:00:00Z")]
    client.batches = {"Suppliers": changed}
    result = ing.run_entity("Suppliers")
    assert client.filters[-1] == "LastModified gt datetime'2026-08-01T10:00:00Z'"
    df = pd.read_parquet(tmp_path / "silver" / "Suppliers.parquet")
    assert len(df) == 2
    assert df.loc[df.SupplierID == 1, "CompanyName"].iloc[0] == "Acme Renamed"


def test_contract_violations_block_write(tmp_path):
    bad = [dict(SUPPLIERS[0], Country="DEU")]  # country must be 2 letters
    client = FakeClient({"Suppliers": bad})
    ing = LakehouseIngestor(client, tmp_path)
    from ingest.schemas import ContractError

    with pytest.raises(ContractError):
        ing.run_entity("Suppliers")
    assert not (tmp_path / "silver" / "Suppliers.parquet").exists()


def test_validate_rows_clean():
    assert validate_rows("Suppliers", SUPPLIERS) == []
