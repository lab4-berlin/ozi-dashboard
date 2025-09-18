import pytest
import requests_mock
import time
import requests
from datetime import datetime
from etl.extract_from_ripe_api import ripe_api_call, API_URL, RETRIES

# Mock data for successful response
SUCCESS_DATA = {
    "messages": [],
    "see_also": [],
    "version": "0.2",
    "data_call_name": "test-call",
    "data_call_status": "supported",
    "cached": False,
    "data": {"key": "value"},
    "query_id": "test-query-id",
    "process_time": 10,
    "server_id": "test-server",
    "build_version": "test-version",
    "status": "ok",
    "status_code": 200,
    "time": "2025-07-31T10:00:00.000000",
}

# Mock data for 500 error response
ERROR_500_DATA = {
    "messages": [["error", "There was a problem handling this request."]],
    "see_also": [],
    "version": "0.2",
    "data_call_name": "test-call",
    "data_call_status": "supported - connecting to Flow",
    "cached": False,
    "data": {},
    "query_id": "test-query-id",
    "process_time": 19,
    "server_id": "app164",
    "build_version": "main-2025.07.16",
    "status": "error",
    "status_code": 500,
    "time": "2025-07-31T10:16:22.289064",
}


def test_ripe_api_call_success():
    """Test successful API call"""
    with requests_mock.Mocker() as m:
        m.get(API_URL.format("test-call"), json=SUCCESS_DATA, status_code=200)
        result = ripe_api_call(API_URL.format("test-call"), {})
        assert result == SUCCESS_DATA


def test_ripe_api_call_500_retry_success():
    """Test API call with 500 error and successful retry"""
    with requests_mock.Mocker() as m:
        # First RETRIES-1 calls return 500, last one succeeds
        # First RETRIES-1 calls return 500, last one succeeds
        for _ in range(RETRIES - 1):
            m.get(API_URL.format("test-call"), json=ERROR_500_DATA, status_code=500)
        m.get(API_URL.format("test-call"), json=SUCCESS_DATA, status_code=200)

        start_time = time.time()
        result = ripe_api_call(API_URL.format("test-call"), {})
        end_time = time.time()

        assert result == SUCCESS_DATA


def test_ripe_api_call_500_max_retries_fail():
    """Test API call with 500 error and max retries reached"""
    with requests_mock.Mocker() as m:
        # All calls return 500
        for _ in range(RETRIES):
            m.get(API_URL.format("test-call"), json=ERROR_500_DATA, status_code=500)

        start_time = time.time()
        result = ripe_api_call(API_URL.format("test-call"), {})
        end_time = time.time()

        assert result is None


def test_ripe_api_call_network_error_max_retries_fail():
    """Test API call with network error and max retries reached"""
    with requests_mock.Mocker() as m:
        # All calls raise a ConnectionError
        for i in range(RETRIES):
            m.get(
                API_URL.format("test-call"),
                exc=requests.exceptions.RequestException("Simulated network error"),
            )

        start_time = time.time()
        result = ripe_api_call(API_URL.format("test-call"), {})
        end_time = time.time()

        assert result is None
