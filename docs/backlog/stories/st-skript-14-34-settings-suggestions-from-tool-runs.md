---
type: story
id: ST-SKRIPT-14-34
title: Settings suggestions from tool runs
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-14
acceptance_criteria:
- Given a tool run returns settings_suggestions, when the UI renders results, then
  a suggestion card appears without showing raw JSON.
- Given a user clicks Save on a settings suggestion, when the backend validates the
  payload, then settings are persisted and applied on future runs.
- Given a suggestion payload fails validation, when the user attempts to save, then
  the UI shows an actionable error and does not persist changes.
- Given a tool does not return settings_suggestions, when rendering results, then
  behavior is unchanged.
retired_ids:
- ST-14-34
---

## Context


Tools may derive reusable settings (e.g., class rosters) from input files. Manual copy/paste into the settings panel is
error-prone and a poor UX. We need a safe, explicit mechanism to suggest settings changes from a run without allowing
the runner to persist settings directly.

## Epic Contract Slice

No separate epic contract slice is stated in the source.

## ADR Coverage

No separate adr coverage is stated in the source.

## Contract Inputs

No separate contract inputs is stated in the source.

## Live Verification Plan

No separate live verification plan is stated in the source.

## Non-Goals

No separate non-goals is stated in the source.

## Notes


- The suggestion payload is non-persistent until the user explicitly saves.
- Validation must reuse the existing settings schema pipeline.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Story Closeout Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
