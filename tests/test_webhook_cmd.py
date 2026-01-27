from ci_hunter.webhook_cmd import main

REPO = "acme/repo"
PR_NUMBER = 21
HEAD_SHA = "abc123"
HEAD_REF = "feature-x"


def _payload_text() -> str:
    return f"""
{{
  "action": "opened",
  "repository": {{"full_name": "{REPO}"}},
  "pull_request": {{
    "number": {PR_NUMBER},
    "head": {{"sha": "{HEAD_SHA}", "ref": "{HEAD_REF}"}}
  }}
}}
""".strip()


def test_webhook_cmd_passes_event_payload_and_dry_run(tmp_path):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(_payload_text(), encoding="utf-8")
    captured: dict[str, object] = {}

    def run_webhook_from_text(event: str, payload_text: str, *, cli_main, extra_args):
        captured.update(
            {
                "event": event,
                "payload_text": payload_text,
                "extra_args": list(extra_args or []),
            }
        )
        return True, 0

    exit_code = main(
        [
            "--event",
            "pull_request",
            "--payload-file",
            str(payload_path),
            "--dry-run",
        ],
        run_webhook_from_text=run_webhook_from_text,
    )

    assert exit_code == 0
    assert captured["event"] == "pull_request"
    assert HEAD_SHA in captured["payload_text"]
    assert captured["extra_args"] == ["--dry-run"]


def test_webhook_cmd_returns_non_zero_when_unhandled(tmp_path):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(_payload_text(), encoding="utf-8")

    exit_code = main(
        [
            "--event",
            "pull_request",
            "--payload-file",
            str(payload_path),
        ],
        run_webhook_from_text=lambda *_args, **_kwargs: (False, None),
    )

    assert exit_code == 1


def test_webhook_cmd_propagates_cli_exit_code(tmp_path):
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(_payload_text(), encoding="utf-8")

    def run_webhook_from_text(event: str, payload_text: str, *, cli_main, extra_args):
        return False, 2

    exit_code = main(
        [
            "--event",
            "pull_request",
            "--payload-file",
            str(payload_path),
        ],
        run_webhook_from_text=run_webhook_from_text,
    )

    assert exit_code == 2
