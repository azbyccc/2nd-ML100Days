"""
Base collector: robots.txt check, rate limiting, retry/backoff, logging.

Every concrete collector must implement fetch() → list[MarketDataPoint].
The collect() entry point wraps fetch() with compliance checks and storage.
"""
from __future__ import annotations

import logging
import time
import urllib.parse
import urllib.robotparser
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

if TYPE_CHECKING:
    from src.schema import MarketDataPoint

logger = logging.getLogger(__name__)

# One shared session per process
_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "FixedIncomeMonitor/1.0 (research; non-commercial)"})


@lru_cache(maxsize=32)
def _robots_allowed(base_url: str, user_agent: str) -> bool:
    """Cached robots.txt check. Returns True if fetch is allowed (or robots.txt unreachable)."""
    robots_url = base_url.rstrip("/") + "/robots.txt"
    rp = urllib.robotparser.RobotFileParser(robots_url)
    try:
        rp.read()
        allowed = rp.can_fetch(user_agent, base_url)
        logger.debug("robots.txt %s → %s", robots_url, "allowed" if allowed else "BLOCKED")
        return allowed
    except Exception as exc:
        logger.warning("Cannot read robots.txt at %s (%s) — assuming allowed", robots_url, exc)
        return True


class BaseCollector(ABC):
    """Abstract base. Subclasses implement fetch() and declare RATE_LIMIT_RPS."""

    USER_AGENT:     str   = "FixedIncomeMonitor/1.0 (research; non-commercial)"
    RATE_LIMIT_RPS: float = 1.0
    SOURCE_NAME:    str   = "UNKNOWN"
    BASE_URL:       str   = ""

    def __init__(self) -> None:
        self._last_ts: float = 0.0

    # ── Public API ────────────────────────────────────────────────────────────

    def collect(self) -> list["MarketDataPoint"]:
        """Compliance-wrapped fetch. Call this from the pipeline."""
        if self.BASE_URL and not _robots_allowed(self.BASE_URL, self.USER_AGENT):
            logger.error("%s: robots.txt blocks access to %s — skipping.", self.SOURCE_NAME, self.BASE_URL)
            return []
        return self.fetch()

    @abstractmethod
    def fetch(self) -> list["MarketDataPoint"]:
        """Fetch data. Return list of MarketDataPoint. Must not raise on partial failure."""

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    def get(self, url: str, **kwargs) -> requests.Response:
        """Rate-limited, retry-enabled GET. Raises on non-2xx after retries."""
        self._throttle()

        @retry(
            retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=2, min=2, max=30),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _do() -> requests.Response:
            resp = _SESSION.get(url, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp

        logger.debug("%s GET %s", self.SOURCE_NAME, url)
        return _do()

    def _throttle(self) -> None:
        interval = 1.0 / self.RATE_LIMIT_RPS
        wait = interval - (time.monotonic() - self._last_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_ts = time.monotonic()
