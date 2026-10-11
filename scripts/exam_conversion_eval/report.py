"""Print principle failure counts, the title verdict and every item mismatch."""

from __future__ import annotations

from .compare_results import ExamComparison


def print_comparison(comparison: ExamComparison) -> None:
    """Print the title verdict, principle counts and complete mismatch details."""
    failures = comparison.failures_by_principle()
    print("  failing items per principle: " + ", ".join(f"{p} {n}" for p, n in failures.items()))
    title = comparison.title
    verdict = "ok" if title.passed else "FAIL"
    print(f"  title {verdict}: gold={title.gold!r} actual={title.actual!r}")
    for item in comparison.items:
        if item.passed:
            continue
        for mismatch in item.mismatches:
            print(
                f"  [{item.index}] {item.source_label} {mismatch.principle} {mismatch.reason}:"
                f" expected={mismatch.expected!r} actual={mismatch.actual!r}"
            )
