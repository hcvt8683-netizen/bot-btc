"""Minimal HTTP client (stdlib only) with retries; every call is read-only public data."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

UA = "Mozilla/5.0 (compatible; bot-btc-research/2.0; +https://github.com/hcvt8683-netizen/bot-btc)"
# some government sites (bls.gov) reject bot-style agents; used only for those calendar pages
UA_PAGE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) bot-btc-research"


class FetchError(RuntimeError):
    """Raised when a source cannot be fetched; carries the HTTP status when known."""

    def __init__(self, url: str, msg: str, status: int | None = None):
        super().__init__(f"{msg} ({url[:120]})")
        self.url, self.status = url, status


def get(url: str, timeout: float = 60, retries: int = 3, backoff: float = 2.0, ua: str = UA) -> bytes:
    """GET a URL and return the body. Retries on network errors and 5xx; 4xx (e.g. 451 geo-block) fail fast."""
    last: Exception | None = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if e.code < 500 and e.code != 429:
                raise FetchError(url, f"HTTP {e.code}", e.code) from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
        time.sleep(backoff * (k + 1))
    status = getattr(last, "code", None)
    raise FetchError(url, f"{type(last).__name__}: {last}", status)


def get_json(url: str, **kw: Any) -> Any:
    return json.loads(get(url, **kw).decode("utf-8"))
