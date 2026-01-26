from __future__ import annotations

from ci_hunter.analyze import AnalysisResult


def render_markdown_report(result: AnalysisResult) -> str:
    lines = [f"# CI Report for {result.repo}", ""]
    if result.regressions:
        lines.append("## Regressions")
        for regression in result.regressions:
            delta_pct = regression.delta_pct * 100
            lines.append(
                f"- {regression.metric}: "
                f"{regression.current:.1f}s vs {regression.baseline:.1f}s "
                f"({delta_pct:+.1f}%)"
            )
    else:
        lines.append("## No regressions detected")
        if result.reason:
            lines.append(f"- Reason: {result.reason}")
    return "\n".join(lines)
