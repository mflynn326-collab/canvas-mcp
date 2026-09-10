"""Thin wrapper around the Canvas LMS REST API.

Handles bearer-token auth, Link-header pagination, throttling backoff,
and turning Canvas's JSON error payloads into readable exceptions.
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterator

import httpx


class CanvasAPIError(Exception):
    """Raised when Canvas returns an error response."""

    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"Canvas API error {status_code} at {url}: {message}")


def _extract_error(response: httpx.Response) -> str:
    try:
        data = response.json()
    except Exception:
        return response.text[:500]
    # Canvas error payloads come in a few shapes:
    # {"errors": [{"message": ...}]}, {"errors": {"field": [{"message": ...}]}},
    # or {"message": ...}
    errors = data.get("errors") if isinstance(data, dict) else None
    if isinstance(errors, list):
        return "; ".join(str(e.get("message", e)) for e in errors)
    if isinstance(errors, dict):
        parts = []
        for field, items in errors.items():
            if isinstance(items, list):
                msgs = ", ".join(str(i.get("message", i)) if isinstance(i, dict) else str(i) for i in items)
                parts.append(f"{field}: {msgs}")
            else:
                parts.append(f"{field}: {items}")
        return "; ".join(parts)
    if isinstance(data, dict) and "message" in data:
        return str(data["message"])
    return str(data)[:500]


class CanvasClient:
    """Authenticated Canvas API client bound to one Canvas instance."""

    MAX_THROTTLE_RETRIES = 4

    def __init__(self, base_url: str | None = None, token: str | None = None):
        base_url = (base_url or os.environ.get("CANVAS_BASE_URL", "")).rstrip("/")
        token = token or os.environ.get("CANVAS_API_TOKEN", "")
        if not base_url:
            raise CanvasAPIError(0, "CANVAS_BASE_URL is not set. Add it to the .env file.", "")
        if not token or token == "paste-your-token-here":
            raise CanvasAPIError(
                0,
                "CANVAS_API_TOKEN is not set. Generate one at Canvas -> Account -> Settings -> "
                "+ New Access Token, and put it in the .env file.",
                "",
            )
        self.base_url = base_url
        self._http = httpx.Client(
            base_url=f"{base_url}/api/v1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._http.close()

    # -- core request helpers -------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Issue a request, retrying with backoff when Canvas throttles us."""
        for attempt in range(self.MAX_THROTTLE_RETRIES + 1):
            response = self._http.request(method, path, **kwargs)
            throttled = response.status_code == 403 and "Rate Limit Exceeded" in response.text
            if not throttled:
                break
            time.sleep(2**attempt)  # 1, 2, 4, 8 seconds
        if response.status_code >= 400:
            raise CanvasAPIError(response.status_code, _extract_error(response), str(response.url))
        return response

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params).json()

    def post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, json=data).json()

    def put(self, path: str, data: dict[str, Any] | None = None) -> Any:
        return self._request("PUT", path, json=data).json()

    def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("DELETE", path, params=params).json()

    def get_paginated(self, path: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        """Yield items across all pages, following Link: rel="next" headers."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        response = self._request("GET", path, params=params)
        while True:
            yield from response.json()
            next_url = response.links.get("next", {}).get("url")
            if not next_url:
                break
            # next_url is absolute and already carries the query string
            response = self._request("GET", next_url)
