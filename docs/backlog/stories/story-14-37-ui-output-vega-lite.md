---
type: story
id: ST-14-37
title: "UI output: vega_lite charts (restricted, enabled for all tools)"
status: ready
owners: "agents"
created: 2026-01-16
epic: "EPIC-14"
links: ["ADR-0022", "ADR-0024"]
acceptance_criteria:
  - "Given a tool run returns a vega_lite output with inline data and within caps, when viewing run results in the SPA, then the platform renders the chart."
  - "Given a tool run returns a vega_lite output that violates restrictions (remote data, caps, composition), when normalizing ui_payload, then the platform deterministically drops the vega_lite output and adds an actionable system notice explaining what was blocked."
  - "Given a tool run is executed in production context by an end user, when the tool returns vega_lite outputs, then the outputs are accepted (policy-enabled) and rendered under the same restrictions as sandbox."
  - "Given a run is replayed from stored ui_payload, when rendering outputs, then vega_lite behavior is deterministic (same normalized spec renders the same chart or the same system notice)."
dependencies:
  - "ADR-0024"
  - "ST-11-07"
ui_impact: "Yes (new chart renderer in run results + sandbox)"
data_impact: "Yes (ui_payload budgets increase; vega_lite specs stored in ui_payload)"
---

## Context

Vega-Lite (`vega_lite`) exists in the UI contract v2 but is currently blocked end-to-end:

- Server normalizer drops `vega_lite` outputs unconditionally.
- SPA renderer is a placeholder component.

Tool developers want to render lightweight charts (e.g. trends over time, distributions) directly in tool results.

## Goal

Enable `vega_lite` output rendering for **all tools in production** (not sandbox-only) under **Option A** minimal
restrictions (defined in ADR-0024):

- Inline-only data (`data.values`), no `data.url`
- `data.values` max rows: 4000
- Spec max bytes: 512 KiB
- Composition caps: max depth 8, max layers 16
- Disallow external resource marks (at least `image`)

## Notes

Implementation requires:

- Domain normalizer support for validating/capping/dropping invalid `vega_lite` outputs with actionable notices.
- Policy enablement for default profile (user-authored tools) plus updated budgets/caps.
- SPA renderer implementation (likely via lazy-loaded Vega embed) with robust fallback on render failure.
