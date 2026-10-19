"""Bronze/silver ingestion pipeline.

Bronze: raw JSONL files, one per run and entity set (append-only landing zone).
Silver: deduplicated Parquet tables, upserted by the entity key, after contract
validation. Incremental loads use a persisted watermark per entity set and query
with $filter=LastModified gt <watermark>.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd

from .client import ODataClient
from .schemas import CONTRACTS, ContractError, validate_rows


class LakehouseIngestor:
    def __init__(self, client: ODataClient, root: str | Path):
        self.client = client
        self.root = Path(root)
        (self.root / "bronze").mkdir(parents=True, exist_ok=True)
        (self.root / "silver").mkdir(parents=True, exist_ok=True)

    def _watermark_path(self, entity_set: str) -> Path:
        return self.root / "silver" / f"{entity_set}.watermark"

    def load_watermark(self, entity_set: str) -> str | None:
        path = self._watermark_path(entity_set)
        return path.read_text().strip() if path.exists() else None

    def save_watermark(self, entity_set: str, watermark: str) -> None:
        self._watermark_path(entity_set).write_text(watermark)

    def run_entity(self, entity_set: str, full_refresh: bool = False) -> dict:
        watermark = None if full_refresh else self.load_watermark(entity_set)
        filter_expr = f"LastModified gt datetime'{watermark}'" if watermark else None
        rows = list(self.client.iter_rows(entity_set, filter_expr))
        if not rows:
            return {"entity_set": entity_set, "fetched": 0, "silver_rows": self._silver_count(entity_set)}

        problems = validate_rows(entity_set, rows)
        if problems:
            raise ContractError(f"{entity_set}: {len(problems)} contract violations: {problems[:5]}")

        run_id = time.strftime("%Y%m%dT%H%M%S")
        bronze_path = self.root / "bronze" / f"{entity_set}-{run_id}.jsonl"
        with bronze_path.open("w") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

        key = CONTRACTS[entity_set]["key"]
        new_df = pd.DataFrame(rows)
        silver_path = self.root / "silver" / f"{entity_set}.parquet"
        if silver_path.exists() and not full_refresh:
            old_df = pd.read_parquet(silver_path)
            merged = pd.concat([old_df, new_df]).drop_duplicates(subset=key, keep="last")
        else:
            merged = new_df.drop_duplicates(subset=key, keep="last")
        merged = merged.sort_values(key).reset_index(drop=True)
        merged.to_parquet(silver_path, index=False)

        self.save_watermark(entity_set, max(r["LastModified"] for r in rows))
        return {
            "entity_set": entity_set,
            "fetched": len(rows),
            "silver_rows": len(merged),
            "bronze_file": str(bronze_path),
        }

    def _silver_count(self, entity_set: str) -> int:
        path = self.root / "silver" / f"{entity_set}.parquet"
        return len(pd.read_parquet(path)) if path.exists() else 0

    def run_all(self, full_refresh: bool = False) -> list[dict]:
        return [self.run_entity(name, full_refresh) for name in CONTRACTS]


def main() -> None:
    base_url = os.environ.get("ODATA_BASE_URL", "http://localhost:8000")
    root = os.environ.get("LAKEHOUSE_ROOT", "./lakehouse")
    full = os.environ.get("FULL_REFRESH", "false").lower() == "true"
    ingestor = LakehouseIngestor(ODataClient(base_url), root)
    for result in ingestor.run_all(full_refresh=full):
        print(result)


if __name__ == "__main__":
    main()
