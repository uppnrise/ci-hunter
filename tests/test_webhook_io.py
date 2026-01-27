import json

import pytest

from ci_hunter.github.webhook_io import load_webhook_payload


def test_load_webhook_payload_parses_json_object():
    payload = {"action": "opened", "repository": {"full_name": "acme/repo"}}

    loaded = load_webhook_payload(json.dumps(payload))

    assert loaded == payload


def test_load_webhook_payload_rejects_non_object_json():
    with pytest.raises(ValueError):
        load_webhook_payload(json.dumps(["not", "an", "object"]))

