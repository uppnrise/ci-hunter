from __future__ import annotations

from ci_hunter.analyze import AnalysisResult
import json


SECTION_RUN = "Run regressions"
SECTION_STEP = "Step regressions"
SECTION_TEST = "Test regressions"
SECTION_NONE = "No regressions detected"
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
            missing_data_note=MISSING_STEP_DATA if result.step_data_missing else None,
        )
    )
    lines.extend(
        _render_regression_section(
            SECTION_TEST,
            result.test_regressions,
            result.test_reason,
            missing_data_note=MISSING_TEST_DATA if result.test_data_missing else None,
        )
    )
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
        "step_data_missing": result.step_data_missing,
        "test_data_missing": result.test_data_missing,
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
