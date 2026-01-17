---
type: pr
id: PR-0037
title: "Editor AI: tolerant diff matching + normalization for LLM patch ops"
status: ready
owners: "agents"
created: 2026-01-17
updated: 2026-01-17
stories:
  - "ST-08-24"
tags: ["backend", "editor", "ai", "diff"]
acceptance_criteria:
  - "Given patch_lines include embedded newlines, preview/apply splits them into per-line entries before validation and apply behavior is deterministic."
  - "Given a diff has valid body context but incorrect hunk ranges, preview/apply can re-anchor headers against base_text and reduce false offset/fuzz warnings."
  - "Given a diff omits a small number of structural base lines between context lines, preview/apply can still match within tight safety bounds (no broad greedy matching)."
  - "Given the relaxed matcher still fails, preview fails with clear error details (expected/base snippets) rather than silent success."
---

## Problem

The current unified-diff matcher is strict about base-context ordering. It only allows blank-line skips between
context lines and only fuzzes leading/trailing context. LLM diffs that look correct can still fail when they omit
one or two non-blank context lines or when their hunk headers are off by a few lines. This creates avoidable
"patch_apply_failed" outcomes and confusing warnings even when the model intent is correct.

## Goal

Make the diff normalizer and matcher resilient to common LLM output variability without compromising safety:
- accept line-list encoding quirks (embedded newlines inside patch_lines entries),
- re-anchor hunk headers to base_text when header line numbers are wrong,
- allow limited, well-scoped non-blank skips between context lines,
- keep existing bounded fuzz and offset safeguards.

## Non-goals

- No UI changes and no new UI warnings.
- No broad greedy search-and-replace or multi-file patch support.
- No change to the patch-only edit-ops contract.

## Implementation plan

1) Patch_lines normalization (safe, always-on)
- Add a helper to flatten patch_lines before joining:
  - Split any entry containing `\n` or `\r\n` into multiple lines (preserve empty lines).
  - Keep the existing trailing newline rule.
- Suggested location: `EditOpsPreviewHandler._join_patch_lines` or a dedicated helper in
  `src/skriptoteket/infrastructure/editor/unified_diff_applier.py`.
- Add a unit test that feeds `patch_lines` with embedded newlines and asserts prepare/apply is identical to the
  per-line equivalent.

2) Header re-anchoring when headers are wrong (safe fallback)
- Add a fallback stage that re-computes hunk header ranges using base_text even when headers exist.
- Suggested approach:
  - In `NativeUnifiedDiffApplier.prepare(...)`, add an optional `reanchor_headers` flag.
  - Build parsed hunks, then for each hunk compute a best match against base_text and rewrite `@@` ranges to
    the matched line offsets (similar to `_repair_missing_hunk_ranges`, but not gated on missing headers).
  - Use this only as a fallback when a strict apply fails or when `max_offset` exceeds a threshold
    (e.g., > 10).
- Keep normalizations list updated (e.g., `reanchored_hunk_ranges`).

3) Limited non-blank skips between context lines (moderate fallback)
- Extend `_match_from` to allow skipping a small number of base lines between expected context lines.
- Safety constraints:
  - Only enabled in a late fallback stage.
  - Require at least two context anchors in the hunk (leading + trailing context lines).
  - Allow only "structural" skips by default (e.g., lines matching `^\s*[}\]),]*\s*$` or comment lines).
  - Hard cap total skips per hunk (e.g., 1-2 lines).
- Suggested API changes:
  - Add `max_extra_skips` and `skip_predicate` to `_match_from` / `_find_hunk_match`.
  - Run a new fallback stage: strict -> whitespace -> fuzz -> structural-skip.

4) Optional internal context drop (aggressive, last resort)
- Allow dropping a small number of internal context lines inside a hunk (not just lead/tail) to handle
  one missing unchanged line in the model output.
- Safety constraints:
  - Only run after step 3 fails.
  - Limit to at most 1-2 dropped lines per hunk.
  - Require a minimum number of remaining context anchors.
- Suggested implementation:
  - Generate a small set of candidate `old_lines` variants with one internal context line removed, then
    run the normal matcher against each candidate.
  - Record a normalization flag such as `dropped_internal_context`.

## Test plan

- Unit: `tests/unit/infrastructure/test_unified_diff_applier.py`
  - Embedded-newline patch_lines normalization.
  - Re-anchored header success when line numbers are off.
  - Structural-skip success for a diff missing a single `},` line in context.
  - Internal context drop only triggers in late fallback, not in strict or whitespace stages.
- Manual (context alignment): run the chat/edit-ops probe to confirm both flows see the same base:
  - `pdm run python scripts/chat_edit_ops_context_probe.py --scenario scripts/edit_ops_scenarios/chat_edit_ops_context_example.json`
  - Inspect `.artifacts/chat-edit-ops-context/<timestamp>/capture_summary.json` for base_hash_match.
- Manual: replay a known failing capture (from `.artifacts/llm-captures/edit_ops_preview_failure/*`) and
  verify preview succeeds or returns a clearer error.

## Rollback plan

- Revert the new fallback stages and keep the existing strict matcher + fuzz ladder.
- No data migrations required.
