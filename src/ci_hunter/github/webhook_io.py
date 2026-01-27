from __future__ import annotations

import json
from typing import Any


def load_webhook_payload(payload_text: str) -> dict[str, Any]:
    payload = json.loads(payload_text)
    if not isinstance(payload, dict):
        raise ValueError("Webhook payload must be a JSON object")
    return payload

