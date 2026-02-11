from ci_hunter.steps import StepDuration, parse_step_durations


def test_parse_step_durations_from_github_log():
    log_text = """
2024-01-01T00:00:00.0000000Z  [command] echo "Start"
2024-01-01T00:00:05.0000000Z  Step: Checkout
2024-01-01T00:00:15.0000000Z  Step: Install deps
2024-01-01T00:00:40.0000000Z  Step: Run tests
2024-01-01T00:01:00.0000000Z  [command] echo "Done"
"""

    durations = parse_step_durations(log_text)

    assert durations == [
        StepDuration(name="Checkout", duration_seconds=10.0),
        StepDuration(name="Install deps", duration_seconds=25.0),
        StepDuration(name="Run tests", duration_seconds=20.0),
    ]


def test_parse_step_durations_handles_utf8_bom_timestamp():
    log_text = """
\ufeff2026-02-11T17:01:13.493987+00:00  Step: Checkout
2026-02-11T17:01:23.493987+00:00  Step: Install deps
2026-02-11T17:01:33.493987+00:00  [command] echo "Done"
"""

    durations = parse_step_durations(log_text)

    assert durations == [
        StepDuration(name="Checkout", duration_seconds=10.0),
        StepDuration(name="Install deps", duration_seconds=10.0),
    ]
