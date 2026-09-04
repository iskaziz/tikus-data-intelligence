"""Small read-only HTTP client for public exhibitor endpoints.

Only GET and JSON POST requests are exposed. There is intentionally no generic
form submission helper and no booking/seat-selection functionality.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "TIKUS-Data-Intelligence/1.0 (+read-only theatrical observation)"


class HttpError(RuntimeError):
    pass


@dataclass(frozen=True)
class Response:
    url: str
    status: int
    body: bytes
    content_type: str | None

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.body).hexdigest()

    def json(self) -> Any:
        return json.loads(self.text)


def _request(request: Request, *, timeout: int = 25, retries: int = 2) -> Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return Response(
                    url=response.geturl(),
                    status=getattr(response, "status", 200),
                    body=response.read(),
                    content_type=response.headers.get("Content-Type"),
                )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
    raise HttpError(f"Request failed after {retries + 1} attempts: {request.full_url}: {last_error}")


def get(url: str, *, headers: dict[str, str] | None = None, timeout: int = 25, retries: int = 2) -> Response:
    merged = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, application/xml, text/xml, text/plain, */*",
    }
    if headers:
        merged.update(headers)
    return _request(Request(url, headers=merged, method="GET"), timeout=timeout, retries=retries)


def post_json(url: str, payload: dict[str, Any], *, headers: dict[str, str] | None = None,
              timeout: int = 25, retries: int = 2) -> Response:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    merged = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    }
    if headers:
        merged.update(headers)
    return _request(Request(url, data=body, headers=merged, method="POST"), timeout=timeout, retries=retries)
