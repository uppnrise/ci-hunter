from __future__ import annotations

import json

from ci_hunter.analyze import AnalysisResult
from ci_hunter.detection import ChangePoint, Flake

SECTION_RUN = "Run regressions"
SECTION_STEP = "Step regressions"
SECTION_TEST = "Test regressions"
SECTION_STEP_CHANGES = "Step change points"
SECTION_TEST_CHANGES = "Test change points"
SECTION_FLAKES = "Flaky tests"
SECTION_NONE = "No regressions detected"
SECTION_NONE_CHANGE_POINTS = "No change points detected"
SECTION_NO_FLAKES = "No flaky tests detected"
REASON_PREFIX = "Reason: "
MISSING_STEP_DATA = "Step data missing"
MISSING_TEST_DATA = "Test data missing"


def render_markdown_report(result: AnalysisResult) -> str:
    lines = [f"# CI Report for {result.repo}", ""]
    lines.extend(_render_regression_section(SECTION_RUN, result.regressions, result.reason))
    lines.extend(
        _render_regression_section(
            SECTION_STEP,
            result.step_regressions,
            result.step_reason,
            missing_data_note=_missing_data_note(
                MISSING_STEP_DATA,
                result.step_timings_attempted,
                result.step_timings_failed,
            ),
        )
    )
    lines.extend(
        _render_regression_section(
            SECTION_TEST,
            result.test_regressions,
            result.test_reason,
            missing_data_note=_missing_data_note(
                MISSING_TEST_DATA,
                result.test_timings_attempted,
                result.test_timings_failed,
            ),
        )
    )
    lines.extend(_render_change_point_section(SECTION_STEP_CHANGES, result.step_change_points))
    lines.extend(_render_change_point_section(SECTION_TEST_CHANGES, result.test_change_points))
    lines.extend(_render_flake_section(result.flakes))
    return "\n".join(lines)


def render_json_report(result: AnalysisResult) -> str:
    payload = {
        "repo": result.repo,
        "regressions": _render_regression_payloads(result.regressions),
        "reason": result.reason,
        "step_regressions": _render_regression_payloads(result.step_regressions),
        "test_regressions": _render_regression_payloads(result.test_regressions),
        "step_reason": result.step_reason,
        "test_reason": result.test_reason,
        "step_timings_attempted": result.step_timings_attempted,
        "step_timings_failed": result.step_timings_failed,
        "test_timings_attempted": result.test_timings_attempted,
        "test_timings_failed": result.test_timings_failed,
        "step_change_points": _render_change_point_payloads(result.step_change_points),
        "test_change_points": _render_change_point_payloads(result.test_change_points),
        "flakes": [
            {
                "test_name": flake.test_name,
                "fail_rate": flake.fail_rate,
                "failures": flake.failures,
                "total_runs": flake.total_runs,
            }
            for flake in result.flakes
        ],
    }
    return json.dumps(payload)


def _render_regression_section(
    title: str,
    regressions: list,
    reason: str | None,
    *,
    missing_data_note: str | None = None,
) -> list[str]:
    lines = [f"## {title}"]
    if regressions:
        for regression in regressions:
            delta_pct = regression.delta_pct * 100
            lines.append(
                f"- {regression.metric}: "
                f"{regression.current:.1f}s vs {regression.baseline:.1f}s "
                f"({delta_pct:+.1f}%)"
            )
        return lines

    lines.append(f"- {SECTION_NONE}")
    if reason:
        lines.append(f"- {REASON_PREFIX}{reason}")
    if missing_data_note:
        lines.append(f"- {missing_data_note}")
    return lines


def _render_regression_payloads(regressions: list) -> list[dict]:
    return [
        {
            "metric": regression.metric,
            "baseline": regression.baseline,
            "current": regression.current,
            "delta_pct": regression.delta_pct,
        }
        for regression in regressions
    ]


def _render_change_point_payloads(change_points: list[ChangePoint]) -> list[dict]:
    return [
        {
            "metric": point.metric,
            "baseline": point.baseline,
            "recent": point.recent,
            "delta_pct": point.delta_pct,
            "window_size": point.window_size,
        }
        for point in change_points
    ]


def _missing_data_note(prefix: str, attempted: int | None, failed: int | None) -> str | None:
    if attempted is None or failed is None:
        return None
    if attempted <= 0 or failed <= 0:
        return None
    return f"{prefix} for {failed}/{attempted} runs"


def _render_flake_section(flakes: list[Flake]) -> list[str]:
    lines = [f"## {SECTION_FLAKES}"]
    if not flakes:
        lines.append(f"- {SECTION_NO_FLAKES}")
        return lines
    for flake in flakes:
        fail_pct = flake.fail_rate * 100
        lines.append(
            f"- {flake.test_name}: "
            f"{flake.failures}/{flake.total_runs} failures ({fail_pct:.1f}% fail rate)"
        )
    return lines


def _render_change_point_section(title: str, change_points: list[ChangePoint]) -> list[str]:
    lines = [f"## {title}"]
    if not change_points:
        lines.append(f"- {SECTION_NONE_CHANGE_POINTS}")
        return lines
    for point in change_points:
        delta_pct = point.delta_pct * 100
        lines.append(
            f"- {point.metric}: "
            f"{point.recent:.1f}s vs {point.baseline:.1f}s "
            f"({delta_pct:+.1f}%) over last {point.window_size} runs"
        )
    return lines
