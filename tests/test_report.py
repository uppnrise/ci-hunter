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
        step_regressions=[],
        test_regressions=[],
        step_reason=None,
        test_reason=None,
        step_data_missing=True,
        test_data_missing=True,
    )

    report = render_markdown_report(result)

    assert "acme/repo" in report
    assert "Run regressions" in report
    assert "Step regressions" in report
    assert "Test regressions" in report
    assert "run_duration_seconds" in report
    assert "+50.0%" in report
    assert "Step data missing" in report
    assert "Test data missing" in report
