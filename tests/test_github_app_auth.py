import httpx
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ci_hunter.github.auth import GitHubAppAuth, InstallationToken
from ci_hunter.github.client import (
    AUTH_SCHEME,
    DEFAULT_BASE_URL,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    HEADER_ACCEPT,
    HEADER_API_VERSION,
    HEADER_AUTHORIZATION,
)

APP_ID = "12345"
INSTALLATION_ID = "999"
TOKEN = "ghs_abc123"
EXPIRES_AT = "2024-01-01T00:10:00Z"
RSA_KEY_SIZE = 2048
RSA_PUBLIC_EXPONENT = 65537


def _generate_private_key_pem() -> str:
    private_key = rsa.generate_private_key(
        public_exponent=RSA_PUBLIC_EXPONENT,
        key_size=RSA_KEY_SIZE,
    )
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem_bytes.decode("utf-8")


@respx.mock
def test_get_installation_token():
    private_key_pem = _generate_private_key_pem()
    auth = GitHubAppAuth(
        app_id=APP_ID,
        installation_id=INSTALLATION_ID,
        private_key_pem=private_key_pem,
    )

    route = respx.post(
        f"{DEFAULT_BASE_URL}/app/installations/{INSTALLATION_ID}/access_tokens",
    ).mock(
        return_value=httpx.Response(
            201,
            json={
                "token": TOKEN,
                "expires_at": EXPIRES_AT,
            },
        )
    )

    token = auth.get_installation_token()

    assert route.called
    request_headers = route.calls[0].request.headers
    assert request_headers[HEADER_AUTHORIZATION].startswith(f"{AUTH_SCHEME} ")
    assert request_headers[HEADER_ACCEPT] == GITHUB_ACCEPT_HEADER
    assert request_headers[HEADER_API_VERSION] == GITHUB_API_VERSION
    assert token == InstallationToken(
        token=TOKEN,
        expires_at=EXPIRES_AT,
    )
