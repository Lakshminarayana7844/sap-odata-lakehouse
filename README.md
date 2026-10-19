# sap-odata-lakehouse

Ingest SAP-style OData services into a small bronze/silver lakehouse: a mock OData API (FastAPI) serves entity sets, and a Python pipeline pulls them with pagination, incremental watermarks, contract validation and Parquet upserts.

Built to show the everyday pattern behind feeding SAP data (OData extractors are the standard source for many BW/4HANA and analytics pipelines) into a lakehouse, with the pieces a reviewer looks for: tests, Docker, CI and honest limits.

## What it does

- **Mock OData service** (`mock_odata/`): OData v4-style JSON (`value`, `@odata.count`, `@odata.nextLink`) for Suppliers, Products and Orders, supporting `$top`, `$skip`, `$count` and `$filter` on `LastModified`. 468 synthetic rows, no real data.
- **Client** (`ingest/client.py`): follows `nextLink` pagination, retries with backoff.
- **Pipeline** (`ingest/pipeline.py`):
  - bronze: raw JSONL per run, append-only
  - silver: Parquet per entity set, upsert by key (`drop_duplicates keep=last`)
  - incremental: per-entity watermark, next run queries `LastModified gt <watermark>`
- **Contracts** (`ingest/schemas.py`): required fields, types and simple business rules per entity set; violations fail the run before anything is written.
- **Tests**: pagination, incremental filter, upsert merge, contract blocking, plus an in-process end-to-end test (full refresh then a no-change incremental run).

## Run it

```bash
pip install -r requirements.txt
python -m pytest -q                       # 6 tests
sh scripts/run_demo.sh                    # starts the mock API, ingests, lists silver tables
```

Or with Docker (no local Python needed):

```bash
docker build -t sap-odata-lakehouse .
docker run --rm sap-odata-lakehouse
```

## Layout

```
mock_odata/     FastAPI mock source service
ingest/         client, contract validation, bronze/silver pipeline
tests/          unit tests plus an in-process end-to-end test
scripts/        demo runner used by the Dockerfile
```

## Design notes

- Watermarks track `max(LastModified)` per entity set, stored next to the silver table. A rerun with no changes fetches zero rows.
- Upserts are key-based merges, which covers both updates and late-arriving rows.
- The mock server and the test suite share one data module, so tests assert against the exact rows the service returns.

## Limits

- Upsert semantics are last-write-wins by arrival order; a real pipeline would order by the source timestamp.
- The filter parser only understands `LastModified gt|ge datetime'...'`, enough for the incremental pattern shown here.
- No schema evolution handling: a new source column lands in bronze but the contract lists the fields silver validates.
- Pagination, filtering and JSON shape follow OData v4 conventions but are not a full OData implementation; that is the point of the mock.

## CI

GitHub Actions runs the test suite and then builds and runs the Docker demo on every push and pull request.
