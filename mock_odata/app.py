"""Minimal OData-style read service used as the ingestion source in tests and demos.

Supports the subset the ingestion client needs: $top, $skip, $filter on
LastModified (gt/ge), $count and nextLink pagination. JSON shape follows OData v4
conventions: a top-level "value" array plus "@odata.count" and "@odata.nextLink".
"""
from __future__ import annotations

import re

from fastapi import FastAPI, Query, Request

from .data import ENTITY_SETS

app = FastAPI(title="Mock SAP OData service")


def _parse_dt(value: str) -> str:
    return value.strip().strip("'")


@app.get("/odata/{entity_set}")
def get_entity_set(
    entity_set: str,
    request: Request,
    top: int | None = Query(default=None, alias="$top"),
    skip: int = Query(default=0, alias="$skip"),
    filter_expr: str | None = Query(default=None, alias="$filter"),
    count: bool = Query(default=False, alias="$count"),
):
    if entity_set not in ENTITY_SETS:
        return {"error": f"unknown entity set {entity_set}"}
    _, rows = ENTITY_SETS[entity_set]
    rows = list(rows)

    if filter_expr:
        m = re.fullmatch(r"LastModified (gt|ge) datetime'([^']+)'", filter_expr)
        if not m:
            return {"error": f"unsupported filter: {filter_expr}"}
        op, raw = m.group(1), _parse_dt(m.group(2))
        if op == "gt":
            rows = [r for r in rows if r["LastModified"] > raw]
        else:
            rows = [r for r in rows if r["LastModified"] >= raw]

    rows = sorted(rows, key=lambda r: r["LastModified"])
    total = len(rows)
    page = rows[skip : skip + top] if top is not None else rows[skip:]

    body: dict = {"value": page}
    if count:
        body["@odata.count"] = total
    if top is not None and skip + top < total:
        params = dict(request.query_params)
        params["$skip"] = str(skip + top)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        body["@odata.nextLink"] = f"/odata/{entity_set}?{query}"
    return body
