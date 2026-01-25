from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Optional

import httpx
import jwt

from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT_SECONDS,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)


DEFAULT_JWT_TTL_SECONDS = 9 * 60
JWT_ISSUED_AT_SKEW_SECONDS = 60


@dataclass(frozen=True)
class InstallationToken:
    token: str
    expires_at: str


class GitHubAppAuth:
    def __init__(
        self,
        *,
        app_id: str,
        installation_id: str,
        private_key_pem: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self._app_id = app_id
        self._installation_id = installation_id
        self._private_key_pem = private_key_pem
        self._base_url = base_url.rstrip("/")

    def get_installation_token(self) -> InstallationToken:
        jwt_token = self._create_jwt()
        response = httpx.post(
            f"{self._base_url}/app/installations/{self._installation_id}/access_tokens",
            headers={
                HEADER_AUTHORIZATION: f"{AUTH_SCHEME} {jwt_token}",
                HEADER_ACCEPT: GITHUB_ACCEPT_HEADER,
                HEADER_API_VERSION: GITHUB_API_VERSION,
            },
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        return InstallationToken(
            token=payload["token"],
            expires_at=payload["expires_at"],
        )

    def _create_jwt(self) -> str:
        now = int(time.time())
        payload = {
            # Allow clock skew between GitHub and the local system.
            "iat": now - JWT_ISSUED_AT_SKEW_SECONDS,
            "exp": now + DEFAULT_JWT_TTL_SECONDS,
            "iss": self._app_id,
        }
        return jwt.encode(payload, self._private_key_pem, algorithm="RS256")
