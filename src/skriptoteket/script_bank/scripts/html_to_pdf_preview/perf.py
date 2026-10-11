"""Timing records appended to the conversion performance log."""

from __future__ import annotations

from time import perf_counter


def perf_record(
    perf: list[dict[str, object]] | None,
    *,
    source: str,
    label: str,
    start: float,
    extra: dict[str, object] | None = None,
) -> None:
    if perf is None:
        return
    duration_ms = round((perf_counter() - start) * 1000.0, 2)
    entry: dict[str, object] = {"source": source, "label": label, "ms": duration_ms}
    if extra:
        entry.update(extra)
    perf.append(entry)


def perf_event(
    perf: list[dict[str, object]] | None,
    *,
    source: str,
    label: str,
    extra: dict[str, object] | None = None,
) -> None:
    if perf is None:
        return
    entry: dict[str, object] = {"source": source, "label": label, "ms": 0.0}
    if extra:
        entry.update(extra)
    perf.append(entry)
