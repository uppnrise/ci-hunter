from unittest import mock

import httpx
import respx

from ci_hunter.github.http import request_with_retry, RETRY_STATUS_CODES


@respx.mock
def test_request_with_retry_retries_on_retryable_status():
    url = "https://api.github.com/retry"
    route = respx.get(url).mock(
        side_effect=[
            httpx.Response(502, json={"error": "bad gateway"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    with mock.patch("time.sleep"):
        response = request_with_retry("GET", url, max_retries=1)

    assert route.call_count == 2
    assert response.json() == {"ok": True}


@respx.mock
def test_request_with_retry_does_not_retry_on_non_retryable_status():
    url = "https://api.github.com/no-retry"
    route = respx.get(url).mock(return_value=httpx.Response(400, json={"error": "bad request"}))

    with mock.patch("time.sleep"):
        try:
            request_with_retry("GET", url, max_retries=3)
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 400
        else:
            raise AssertionError("Expected HTTPStatusError")

    assert route.call_count == 1


@respx.mock
def test_request_with_retry_retries_on_request_error():
    url = "https://api.github.com/request-error"
    route = respx.get(url).mock(side_effect=httpx.RequestError("boom", request=httpx.Request("GET", url)))

    with mock.patch("time.sleep"):
        try:
            request_with_retry("GET", url, max_retries=1)
        except httpx.RequestError:
            pass
        else:
            raise AssertionError("Expected RequestError")

    assert route.call_count == 2


def test_retry_status_codes_are_non_empty():
    assert RETRY_STATUS_CODES


@respx.mock
def test_request_with_retry_honors_retry_after_header():
    url = "https://api.github.com/retry-after"
    route = respx.get(url).mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )

    with mock.patch("time.sleep") as sleeper:
        response = request_with_retry("GET", url, max_retries=1)

    assert route.call_count == 2
    sleeper.assert_called()
    assert sleeper.call_args.args[0] >= 2
    assert response.json() == {"ok": True}
