"""Focused PR-0213 Playwright entrypoint for launch-trace parity proof."""

from __future__ import annotations

import sys

from scripts._playwright_flunk_out_frenzy_launch_trace_parity import run


def main() -> None:
    """Run the focused child collector and report the artifact path."""

    artifacts = run(sys.argv[1:])
    print(
        "playwright-flunk-out-frenzy-launch-trace-parity: ok "
        f"-> raw={artifacts.raw_artifact_path} "
        f"summary_json={artifacts.summary_json_path} "
        f"summary_md={artifacts.summary_markdown_path}"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
