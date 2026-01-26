import json

from ci_hunter.analyze import AnalysisResult
from ci_hunter.detection import Regression
from ci_hunter.report import render_json_report


def test_render_json_report():
    result = AnalysisResult(
        repo="acme/repo",
        regressions=[
            Regression(
                metric="run_duration_seconds",
                baseline=10.0,
                current=15.0,
                delta_pct=0.5,
            )
        ],
        reason=None,
        step_regressions=[
            Regression(
                metric="Checkout",
                baseline=5.0,
                current=10.0,
                delta_pct=1.0,
            )
        ],
        test_regressions=[
            Regression(
                metric="tests.test_alpha",
                baseline=1.0,
                current=2.0,
                delta_pct=1.0,
            )
        ],
        step_reason=None,
        test_reason=None,
        step_timings_attempted=10,
        step_timings_failed=3,
        test_timings_attempted=10,
        test_timings_failed=4,
    )

    report = render_json_report(result)
    payload = json.loads(report)

    assert payload["repo"] == "acme/repo"
    assert payload["regressions"][0]["metric"] == "run_duration_seconds"
    assert payload["regressions"][0]["delta_pct"] == 0.5
    assert payload["step_regressions"][0]["metric"] == "Checkout"
    assert payload["test_regressions"][0]["metric"] == "tests.test_alpha"
    assert payload["step_timings_attempted"] == 10
    assert payload["step_timings_failed"] == 3
    assert payload["test_timings_attempted"] == 10
    assert payload["test_timings_failed"] == 4
