from ci_hunter.analyze import AnalysisResult
from ci_hunter.detection import Flake, Regression
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
        step_timings_attempted=10,
        step_timings_failed=3,
        test_timings_attempted=10,
        test_timings_failed=4,
        flakes=[
            Flake(
                test_name="tests.alpha::test_x",
                fail_rate=0.4,
                failures=2,
                total_runs=5,
            )
        ],
    )

    report = render_markdown_report(result)

    assert "acme/repo" in report
    assert "Run regressions" in report
    assert "Step regressions" in report
    assert "Test regressions" in report
    assert "run_duration_seconds" in report
    assert "+50.0%" in report
    assert "Step data missing for 3/10 runs" in report
    assert "Test data missing for 4/10 runs" in report
    assert "Flaky tests" in report
    assert "tests.alpha::test_x" in report
