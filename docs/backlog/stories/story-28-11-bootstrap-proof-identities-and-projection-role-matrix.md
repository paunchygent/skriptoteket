---
type: story
id: ST-28-11
title: "Bootstrap proof identities and projection role matrix"
status: ready
owners: "agents"
created: 2026-04-13
updated: 2026-04-13
epic: "EPIC-28"
acceptance_criteria:
  - "Given HuleEdu `TASK-0326` is done and deployed, when this story starts implementation, then it consumes the verified provider subject export instead of inventing local identity data."
  - "Given HuleEdu owns Identity users, when Skriptoteket prepares dev or production auth proof, then it consumes a HuleEdu-provided subject export rather than creating passwords or identity users locally."
  - "Given proof accounts are bootstrapped, when Skriptoteket creates or updates local records, then `identity_projections` are keyed by `product_identity_realm` plus `realm_subject_id` and local `User.role` is assigned only from an explicit Skriptoteket-owned role matrix."
  - "Given existing alpha users mostly use fake education-domain addresses, when this story runs, then it does not bulk import or preserve those users as a launch blocker."
  - "Given the bootstrap is rerun, when the same subject export is applied, then local users, projections, and role assignments remain idempotent and auditable."
  - "Given final cross-app proof needs role coverage, when `ST-28-04` runs, then it can log in as the required Skriptoteket roles without manual database patching."
ui_impact: "No direct UI change; enables role-specific auth proof accounts."
dependencies: ["ADR-0083", "ST-28-09", "HuleEdu TASK-0326", "REV-TASK-0326-01"]
---

## Context

Production still contains the old Skriptoteket-local users, but HuleEdu Identity
has no matching production projections for them. The launch-critical path should
not become a bulk-import project for fake alpha education-domain accounts.

The corrected responsibility split is:

- HuleEdu creates or verifies the small provider-owned proof identity set and
  exports stable subject IDs through `TASK-0326`.
- Skriptoteket creates or updates local `User` rows, local roles, and
  `identity_projections` for the proof role matrix.
- Existing local alpha users can stay as historical data until a later explicit
  cleanup or one-off linking task is approved.

## Notes

- Keep local authorization in Skriptoteket. HuleEdu role or group claims are not
  product authorization for this app.
- Treat the HuleEdu subject export as input, not as a source of secrets.
- Do not implement until HuleEdu `REV-TASK-0326-01` approves the corrected
  `TASK-0326` schema. This gate is now resolved: HuleEdu `REV-TASK-0326-01` is
  approved, `TASK-0326` is done, deployed at merge commit `92419293`, and the
  production proof accounts were verified on Hemma.
- The role matrix must cover at least `user`, `admin`, and `superuser`; include
  `contributor` if the active final proof still exercises that role.
- This story unlocks `PR-0254` but does not replace the final cross-app smoke.
