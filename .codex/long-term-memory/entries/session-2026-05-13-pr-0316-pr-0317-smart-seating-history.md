---
type: agent_session_long_term_memory_entry
id: session-2026-05-13-pr-0316-pr-0317-smart-seating-history
status: active
created: '2026-05-13'
---

# PR-0316 / PR-0317 Smart Seating History

This entry compacts non-current handoff history for the Klassrumskartan smart
seating lane so `.codex/handoff.md` can stay under the live-session budget.

## Retained State

- `PR-0316` remains done and approved; its no-checkpoint soft-degrade contract
  is unchanged.
- `PR-0317` is marked `done` in
  `docs/backlog/prs/pr-0317-st-27-03-smart-seating-history-diversity-scoring.md`.
- Added `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating_history.py`
  to summarize accepted seating checkpoints for anti-repeat scoring.
- Added focused scoring/search helpers under
  `src/skriptoteket/domain/curated_apps/classroom_planner/smart_seating_history_scoring.py`,
  `smart_seating_pattern_scoring.py`, and `smart_seating_search.py`.
- Smart seating candidate scoring includes bounded history-backed diversity for
  non-fixed full layouts, per-student seat/block/zone/front-rank reuse,
  `Håll nära` unordered pair reuse, and `Håll isär` unordered seat-pair plus
  spread-pattern reuse.
- Two-student `Håll isär` pairs are selected jointly instead of one student at
  a time, avoiding deterministic anchoring into two common block patterns.
- Added a G104 normal-rule 10-run simulation proof that counts unordered
  teacher-visible rule block patterns, not in-pair swaps.
- `Fast plats` remains hard seeded and excluded from layout/per-student
  variation penalties.
- Same-draft near-teacher rotation derives its rotation step from the current
  assignment fingerprint to avoid deterministic two-cycles.

## Verification Retained From Handoff

- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver_bf25_g104.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_solver_g104_normal_rules.py -q --override-ini addopts=''`
- `pdm run pytest tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_near_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_keep_apart_geometry.py tests/unit/domain/curated_apps/classroom_planner/test_smart_seating_fixed_seats.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_seating.py tests/unit/web/apps/classroom_planner/test_smart_seating_api.py -q`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
