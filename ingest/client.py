"""OData client with nextLink pagination and simple retry with backoff."""
from __future__ import annotations

import time
from typing import Any, Iterator

import requests


class ODataClient:
    def __init__(self, base_url: str, page_size: int = 50, max_retries: int = 3, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.page_size = page_size
        self.max_retries = max_retries
        self.timeout = timeout

    def _get(self, path_or_url: str) -> dict[str, Any]:
        url = path_or_url if path_or_url.startswith("http") else self.base_url + path_or_url
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:  # connection, timeout, HTTP 5xx/4xx
                last_error = exc
                time.sleep(0.2 * (attempt + 1))
        raise RuntimeError(f"GET {url} failed after {self.max_retries} tries: {last_error}")

    def iter_rows(self, entity_set: str, filter_expr: str | None = None) -> Iterator[dict[str, Any]]:
        query = f"$top={self.page_size}&$count=true"
        if filter_expr:
            query += f"&$filter={filter_expr}"
        path = f"/odata/{entity_set}?{query}"
        while True:
            body = self._get(path)
            yield from body.get("value", [])
            next_link = body.get("@odata.nextLink")
            if not next_link:
                break
            path = next_link

    def max_last_modified(self, entity_set: str, rows: list[dict[str, Any]]) -> str | None:
        if not rows:
            return None
        return max(r["LastModified"] for r in rows)
