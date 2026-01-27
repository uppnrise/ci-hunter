from ci_hunter.github.webhook import WebhookTrigger, parse_pull_request_webhook

REPO = "acme/repo"
PR_NUMBER = 42
HEAD_SHA = "abc123"
HEAD_REF = "feature-x"


def test_parse_pull_request_webhook_opened():
    payload = {
        "action": "opened",
        "repository": {"full_name": REPO},
        "pull_request": {
            "number": PR_NUMBER,
            "head": {"sha": HEAD_SHA, "ref": HEAD_REF},
        },
    }

    trigger = parse_pull_request_webhook("pull_request", payload)

    assert trigger == WebhookTrigger(
        repo=REPO,
        pr_number=PR_NUMBER,
        commit=HEAD_SHA,
        branch=HEAD_REF,
        action="opened",
    )


def test_parse_pull_request_webhook_ignores_other_events():
    payload = {"action": "opened"}

    assert parse_pull_request_webhook("push", payload) is None


def test_parse_pull_request_webhook_handles_malformed_payloads():
    payload = {
        "action": "opened",
        "repository": None,
        "pull_request": None,
    }

    assert parse_pull_request_webhook("pull_request", payload) is None
