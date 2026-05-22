"""Unit tests for the async RIPE client.

Covers retry behaviour for 429/5xx/transport errors, ``Retry-After`` parsing,
final-failure handling, and that concurrent calls never exceed the configured
client-side concurrency cap.
"""

import asyncio

import httpx
import pytest
import pytest_asyncio
import respx

import extract_from_ripe_api_async as mod


SUCCESS_PAYLOAD = {
    "status": "ok",
    "status_code": 200,
    "data": {"key": "value"},
}


@pytest_asyncio.fixture(autouse=True)
async def _reset_module_state():
    mod.reset_stats()
    if mod._client is not None:
        await mod.aclose_client()

    original_initial = mod.RIPE_BACKOFF_INITIAL_S
    original_max = mod.RIPE_BACKOFF_MAX_S
    original_attempts = mod.RIPE_MAX_ATTEMPTS
    mod.RIPE_BACKOFF_INITIAL_S = 0.001
    mod.RIPE_BACKOFF_MAX_S = 0.005
    mod.RIPE_MAX_ATTEMPTS = 6

    yield

    mod.RIPE_BACKOFF_INITIAL_S = original_initial
    mod.RIPE_BACKOFF_MAX_S = original_max
    mod.RIPE_MAX_ATTEMPTS = original_attempts
    if mod._client is not None:
        await mod.aclose_client()


@pytest.mark.asyncio
@respx.mock
async def test_success_returns_payload_and_counts_one_request():
    route = respx.get("https://stat.ripe.net/data/test-call/data.json").mock(
        return_value=httpx.Response(200, json=SUCCESS_PAYLOAD)
    )

    result = await mod.ripe_api_call(mod.API_URL.format("test-call"), {})

    assert result == SUCCESS_PAYLOAD
    assert route.call_count == 1
    assert mod.STATS["requests"] == 1
    assert mod.STATS["retries"] == 0
    assert mod.STATS["final_failures"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_500_then_success_retries_once():
    route = respx.get("https://stat.ripe.net/data/test-call/data.json").mock(
        side_effect=[
            httpx.Response(500, json={"status": "error"}),
            httpx.Response(200, json=SUCCESS_PAYLOAD),
        ]
    )

    result = await mod.ripe_api_call(mod.API_URL.format("test-call"), {})

    assert result == SUCCESS_PAYLOAD
    assert route.call_count == 2
    assert mod.STATS["status_5xx"] == 1
    assert mod.STATS["retries"] == 1
    assert mod.STATS["final_failures"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_all_503_returns_none_and_increments_final_failures():
    route = respx.get("https://stat.ripe.net/data/test-call/data.json").mock(
        return_value=httpx.Response(503, json={"status": "error"})
    )

    result = await mod.ripe_api_call(mod.API_URL.format("test-call"), {})

    assert result is None
    assert route.call_count == mod.RIPE_MAX_ATTEMPTS
    assert mod.STATS["status_5xx"] == mod.RIPE_MAX_ATTEMPTS
    assert mod.STATS["final_failures"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_429_is_retried_and_counted(monkeypatch):
    """End-to-end: a 429 followed by a 200 yields the 200 and counts the 429.

    The actual ``Retry-After`` honoring is unit-tested in
    ``test_wait_strategy_honors_retry_after`` below; here we just want to
    confirm the retry path is wired up without making the test wait.
    """
    waits = []
    original_strategy = mod._wait_strategy

    def fast_strategy(retry_state):
        waits.append(original_strategy(retry_state))
        return 0.0

    monkeypatch.setattr(mod, "_wait_strategy", fast_strategy)

    route = respx.get("https://stat.ripe.net/data/test-call/data.json").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}, json={"status": "error"}),
            httpx.Response(200, json=SUCCESS_PAYLOAD),
        ]
    )

    result = await mod.ripe_api_call(mod.API_URL.format("test-call"), {})

    assert result == SUCCESS_PAYLOAD
    assert route.call_count == 2
    assert mod.STATS["status_429"] == 1
    assert waits and waits[0] >= 2.0, (
        f"wait strategy did not honor Retry-After=2: got {waits}"
    )


def test_wait_strategy_honors_retry_after():
    """``_wait_strategy`` must return at least the Retry-After hint."""

    class _FakeOutcome:
        def __init__(self, exc):
            self._exc = exc

        def exception(self):
            return self._exc

    class _FakeState:
        def __init__(self, exc):
            self.attempt_number = 1
            self.outcome = _FakeOutcome(exc)
            self.idle_for = 0.0

    mod.RIPE_BACKOFF_INITIAL_S = 0.001
    mod.RIPE_BACKOFF_MAX_S = 0.01

    exc = mod._RipeRetryable("http:429", retry_after=3.5)
    wait = mod._wait_strategy(_FakeState(exc))
    assert wait >= 3.5

    exc_no_hint = mod._RipeRetryable("http:500")
    wait = mod._wait_strategy(_FakeState(exc_no_hint))
    assert 0.0 <= wait <= mod.RIPE_BACKOFF_MAX_S + 1.0


@pytest.mark.asyncio
@respx.mock
async def test_transport_error_then_success_retries():
    route = respx.get("https://stat.ripe.net/data/test-call/data.json").mock(
        side_effect=[
            httpx.ConnectError("simulated connection failure"),
            httpx.Response(200, json=SUCCESS_PAYLOAD),
        ]
    )

    result = await mod.ripe_api_call(mod.API_URL.format("test-call"), {})

    assert result == SUCCESS_PAYLOAD
    assert route.call_count == 2
    assert mod.STATS["transport_errors"] == 1
    assert mod.STATS["retries"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_is_retried_then_succeeds():
    route = respx.get("https://stat.ripe.net/data/test-call/data.json").mock(
        side_effect=[
            httpx.Response(200, content=b"not json"),
            httpx.Response(200, json=SUCCESS_PAYLOAD),
        ]
    )

    result = await mod.ripe_api_call(mod.API_URL.format("test-call"), {})

    assert result == SUCCESS_PAYLOAD
    assert route.call_count == 2
    assert mod.STATS["json_errors"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_concurrency_cap_is_enforced():
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()

    async def slow_handler(request):
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        try:
            await asyncio.sleep(0.05)
            return httpx.Response(200, json=SUCCESS_PAYLOAD)
        finally:
            async with lock:
                in_flight -= 1

    respx.get("https://stat.ripe.net/data/test-call/data.json").mock(
        side_effect=slow_handler
    )

    fanout = mod.CONCURRENCY * 4
    results = await asyncio.gather(
        *[
            mod.ripe_api_call(mod.API_URL.format("test-call"), {"i": i})
            for i in range(fanout)
        ]
    )

    assert all(r == SUCCESS_PAYLOAD for r in results)
    assert max_in_flight <= mod.CONCURRENCY, (
        f"max in-flight {max_in_flight} exceeded cap {mod.CONCURRENCY}"
    )


def test_parse_retry_after_handles_seconds_and_http_date():
    assert mod._parse_retry_after("0") == 0.0
    assert mod._parse_retry_after("5") == 5.0
    assert mod._parse_retry_after("not-a-date") is None
    assert mod._parse_retry_after(None) is None
    assert mod._parse_retry_after("") is None
    assert mod._parse_retry_after("Wed, 21 Oct 2099 07:28:00 GMT") is not None
