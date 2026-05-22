"""Async RIPEstat client built on httpx + tenacity.

Mirrors the public surface of ``extract_from_ripe_api`` for the endpoints used
by the neighbours pipeline, but issues requests concurrently against a bounded
connection pool (RIPEstat caps callers at 8 concurrent requests per IP).
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import httpx
import tenacity

from extract_from_ripe_api import save_api_response

API_URL = "https://stat.ripe.net/data/{}/data.json"

CONCURRENCY = int(os.getenv("OZI_RIPE_CONCURRENCY", "6"))
RIPE_TIMEOUT_S = float(os.getenv("OZI_RIPE_TIMEOUT", "30"))
RIPE_CONNECT_TIMEOUT_S = float(os.getenv("OZI_RIPE_CONNECT_TIMEOUT", "5"))
RIPE_MAX_ATTEMPTS = int(os.getenv("OZI_RIPE_MAX_ATTEMPTS", "6"))
RIPE_BACKOFF_INITIAL_S = float(os.getenv("OZI_RIPE_BACKOFF_INITIAL", "1"))
RIPE_BACKOFF_MAX_S = float(os.getenv("OZI_RIPE_BACKOFF_MAX", "60"))

USER_AGENT = os.getenv(
    "OZI_RIPE_USER_AGENT",
    "ozi-dashboard-etl/1.0 (+https://github.com/lab4-berlin/ozi-dashboard)",
)

logger = logging.getLogger(__name__)

STATS = {
    "requests": 0,
    "retries": 0,
    "status_429": 0,
    "status_5xx": 0,
    "transport_errors": 0,
    "json_errors": 0,
    "final_failures": 0,
}


def reset_stats() -> None:
    for k in STATS:
        STATS[k] = 0


def snapshot_stats() -> dict:
    return dict(STATS)


class _RipeRetryable(Exception):
    """Internal marker raised to signal a retryable failure to tenacity."""

    def __init__(self, reason: str, retry_after: Optional[float] = None):
        super().__init__(reason)
        self.reason = reason
        self.retry_after = retry_after


_client: Optional[httpx.AsyncClient] = None
_client_lock = asyncio.Lock()
_semaphore = asyncio.Semaphore(CONCURRENCY)


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = httpx.AsyncClient(
                    timeout=httpx.Timeout(
                        timeout=RIPE_TIMEOUT_S,
                        connect=RIPE_CONNECT_TIMEOUT_S,
                    ),
                    limits=httpx.Limits(
                        max_connections=CONCURRENCY,
                        max_keepalive_connections=CONCURRENCY,
                    ),
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=True,
                )
    return _client


async def aclose_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = (dt - datetime.now(tz=timezone.utc)).total_seconds()
        return max(0.0, delta)
    except (TypeError, ValueError):
        return None


def _wait_strategy(retry_state: tenacity.RetryCallState) -> float:
    base = tenacity.wait_exponential_jitter(
        initial=RIPE_BACKOFF_INITIAL_S, max=RIPE_BACKOFF_MAX_S
    )(retry_state)
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if isinstance(exc, _RipeRetryable) and exc.retry_after is not None:
        return max(base, exc.retry_after)
    return base


def _before_sleep(retry_state: tenacity.RetryCallState) -> None:
    STATS["retries"] += 1
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    reason = getattr(exc, "reason", repr(exc))
    logger.warning(
        "RIPE retry attempt=%d reason=%s next_wait=%.2fs",
        retry_state.attempt_number,
        reason,
        retry_state.next_action.sleep if retry_state.next_action else 0.0,
    )


async def _do_request(url: str, params: dict) -> dict:
    client = await _get_client()
    STATS["requests"] += 1
    try:
        async with _semaphore:
            response = await client.get(url, params=params)
    except (httpx.TransportError, asyncio.TimeoutError) as e:
        STATS["transport_errors"] += 1
        raise _RipeRetryable(f"transport:{type(e).__name__}") from e

    status = response.status_code
    if status == 429:
        STATS["status_429"] += 1
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        raise _RipeRetryable("http:429", retry_after=retry_after)
    if 500 <= status < 600:
        STATS["status_5xx"] += 1
        retry_after = _parse_retry_after(response.headers.get("Retry-After"))
        raise _RipeRetryable(f"http:{status}", retry_after=retry_after)
    if status >= 400:
        response.raise_for_status()

    try:
        return response.json()
    except json.JSONDecodeError as e:
        STATS["json_errors"] += 1
        raise _RipeRetryable("json_decode") from e


async def ripe_api_call(url: str, params: dict) -> Optional[dict]:
    """Fetch ``url`` with ``params`` from RIPEstat, retrying transient errors.

    Returns ``None`` after exhausting retries so callers can keep their
    existing null-checks (mirrors the sync ``extract_from_ripe_api.ripe_api_call``).
    """
    retrying = tenacity.AsyncRetrying(
        retry=tenacity.retry_if_exception_type(_RipeRetryable),
        stop=tenacity.stop_after_attempt(RIPE_MAX_ATTEMPTS),
        wait=_wait_strategy,
        before_sleep=_before_sleep,
        reraise=True,
    )
    try:
        async for attempt in retrying:
            with attempt:
                return await _do_request(url, params)
    except _RipeRetryable as e:
        STATS["final_failures"] += 1
        logger.error("RIPE final failure url=%s reason=%s", url, e.reason)
        return None
    return None


async def get_country_asns(country_iso2, date, save_mode=None):
    url = API_URL.format("country-asns")
    params = {"resource": country_iso2, "query_time": date.isoformat(), "lod": 1}
    data = await ripe_api_call(url, params)

    if save_mode and data is not None:
        save_api_response(url, params, data, save_mode)
    return data


async def get_asn_neighbours(asn, date, save_mode=None):
    url = API_URL.format("asn-neighbours")
    params = {"resource": asn, "query_time": date.isoformat()}
    data = await ripe_api_call(url, params)

    if save_mode and data is not None:
        save_api_response(url, params, data, save_mode)
    return data
