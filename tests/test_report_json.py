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
    )

    report = render_json_report(result)
    payload = json.loads(report)

    assert payload["repo"] == "acme/repo"
    assert payload["regressions"][0]["metric"] == "run_duration_seconds"
    assert payload["regressions"][0]["delta_pct"] == 0.5
