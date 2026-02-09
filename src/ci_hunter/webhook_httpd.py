from __future__ import annotations

import hashlib
import hmac
from http import HTTPStatus
from typing import Any, Callable, Mapping, Tuple

from ci_hunter.webhook_http import handle_webhook_http

SIGNATURE_HEADER = "x-hub-signature-256"
SIGNATURE_PREFIX = "sha256="
AUTH_TOKEN_HEADER = "x-ci-hunter-token"


def handle_request_bytes(
    *,
    method: str,
    headers: Mapping[str, str],
    body_bytes: bytes,
    enqueue_handler: Callable[[str, dict[str, Any]], bool],
    max_body_bytes: int = 1024 * 1024,
    shared_secret: str | None = None,
    auth_token: str | None = None,
) -> Tuple[HTTPStatus, bytes]:
    if len(body_bytes) > max_body_bytes:
        return HTTPStatus.REQUEST_ENTITY_TOO_LARGE, b"payload too large"
    normalized = {key.lower(): value for key, value in headers.items()}
    if auth_token is not None:
        provided = normalized.get(AUTH_TOKEN_HEADER)
        if provided is None or not hmac.compare_digest(provided, auth_token):
            return HTTPStatus.UNAUTHORIZED, b"unauthorized"
    if shared_secret is not None and not _is_valid_signature(normalized, body_bytes, shared_secret):
        return HTTPStatus.UNAUTHORIZED, b"invalid signature"
    try:
        body_text = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return HTTPStatus.BAD_REQUEST, b"invalid utf-8"
    status, body = handle_webhook_http(
        headers=headers,
        body_text=body_text,
        enqueue_handler=enqueue_handler,
    )
    return status, body.encode("utf-8")


def _is_valid_signature(headers: Mapping[str, str], body_bytes: bytes, shared_secret: str) -> bool:
    value = headers.get(SIGNATURE_HEADER)
    if value is None or not value.startswith(SIGNATURE_PREFIX):
        return False
    expected = hmac.new(
        shared_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    provided = value[len(SIGNATURE_PREFIX) :]
    return hmac.compare_digest(provided, expected)
