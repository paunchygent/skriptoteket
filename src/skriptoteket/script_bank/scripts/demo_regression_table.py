"""
Demo: Table column order regression test.

Purpose:
- Dedicated tool for Playwright E2E test (ST-11-07)
- Tests that table outputs render columns in declared order, not object key iteration order
- Isolates test from demo-next-actions to prevent source code pollution

Runner contract:
- Entrypoint: run_tool(input_dir: str, output_dir: str) -> dict
"""

from __future__ import annotations


def run_tool(input_dir: str, output_dir: str) -> dict:
    """Return a table with columns in specific order for regression testing."""
    return {
        "outputs": [
            {
                "kind": "table",
                "title": "Regression table",
                "columns": [
                    {"key": "10", "label": "Ten"},
                    {"key": "2", "label": "Two"},
                ],
                "rows": [
                    {"10": "TEN", "2": "TWO"},
                ],
            }
        ],
        "next_actions": [],
        "state": None,
    }
