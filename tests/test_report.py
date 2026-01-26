from ci_hunter.analyze import AnalysisResult
from ci_hunter.detection import Regression
from ci_hunter.report import render_markdown_report


def test_render_markdown_report():
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

    report = render_markdown_report(result)

    assert "acme/repo" in report
    assert "run_duration_seconds" in report
    assert "+50.0%" in report
