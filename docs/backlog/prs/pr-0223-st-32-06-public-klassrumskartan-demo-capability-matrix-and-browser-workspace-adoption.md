---
type: pr
id: PR-0223
title: "ST-32-06: public Klassrumskartan demo capability matrix and browser-workspace adoption"
status: ready
owners: "agents"
created: 2026-04-05
updated: 2026-04-05
stories:
  - "ST-32-06"
tags: ["frontend", "backend", "klassrumskartan", "public-access", "guest-workspace"]
dependencies:
  - "ADR-0079"
  - "ST-32-04"
  - "ST-32-05"
  - "EPIC-27"
  - "EPIC-29"
acceptance_criteria:
  - "Given Klassrumskartan becomes the first concrete public browser-workspace consumer, when this slice is specified and implemented, then guest-allowed, guest-altered, and guest-blocked behavior is explicit across rosters, templates, smart rules, drafts, history, smart runs, import preview, export, reset, and authenticated-only affordances."
  - "Given the public Klassrumskartan demo is browser-owned, when guest users create or edit rosters, templates, smart rules, or drafts, then those changes persist only in the browser workspace and are not re-homed into account-owned APIs before an explicit authenticated upgrade later occurs."
  - "Given guest Klassrumskartan still needs parser- or compute-assisted flows, when import preview or smart compute runs, then the public helper namespace remains stateless and durable guest continuity stays browser-owned."
  - "Given guest export is available, when a guest user exports, then the result is delivered as an immediate direct download without Vault/MyFiles recovery or resumable account-owned job surfaces."
  - "Given a guest user later authenticates, when the first authenticated visit to Klassrumskartan detects pending guest work, then the existing authenticated upgrade prompt from ST-32-05 appears; and generic login/registration flows outside the app do not trigger migration behavior."
  - "Given the guest demo includes a reset affordance, when the user clears the workspace, then the action is labeled `Rensa arbetsyta`, uses plain-language browser/shared-device confirmation copy, and removes browser-owned guest state without implying account-side deletion."
---

## Problem

`ST-32-04` and `ST-32-05` established the browser-owned snapshot contract and
authenticated upgrade boundary, but Klassrumskartan still lacks the consumer
slice that turns those foundations into a real public demo with an explicit
capability matrix.

Without one connected implementation task, the current story risks drifting in
three ways:

1. guest capability boundaries remain implied instead of locked across the
   actual Klassrumskartan surfaces
2. public helper flows can accidentally expand into hidden account-owned
   persistence or export-job behavior
3. browser-owned reset, first-authenticated-visit upgrade, and blocked
   authenticated-only affordances can land inconsistently across the public host

## Goal

Ship Klassrumskartan as the first honest public browser-workspace demo with:

- full browser-owned guest authoring for rosters, templates, smart rules, and
  drafts
- stateless server assistance for import preview and smart compute only
- direct-download export only
- explicit and honest blocking/signposting for account-owned affordances
- upgrade prompting only on the first authenticated Klassrumskartan visit
- a user-facing `Rensa arbetsyta` affordance with plain-language confirmation

## Non-goals

- No global guest-import abstraction beyond Klassrumskartan's bounded seams.
- No revival of `PR-0222` metadata-only checkpoint compatibility.
- No silent migration on registration, generic site login, or incidental auth
  changes.
- No guest use of Vault/MyFiles, export-job recovery, or account-owned history
  centers.
- No dilution of the existing authenticated planner/API model.

## Locked decisions for this slice

### 1. Guest capability posture

- Guest users can fully author rosters, templates, smart rules, and drafts in
  the browser-owned workspace.
- Authenticated-only assets remain owner-scoped until an explicit later upgrade.

### 2. Server assistance boundary

- Import preview and smart compute may use public helper APIs.
- Those flows must stay stateless; durable guest continuity remains browser
  owned.

### 3. Export boundary

- Guest export is immediate direct download only.
- No guest-facing job center, recovery lane, or Vault/MyFiles artifact history.

### 4. Upgrade trigger

- Detect and offer upgrade only on the first authenticated visit to
  Klassrumskartan.
- Do not trigger upgrade during registration or on generic auth changes
  elsewhere in the product.

### 5. Reset affordance

- The visible action label is `Rensa arbetsyta`.
- Confirmation copy explains browser/shared-device implications in plain
  language without exposing internal storage terminology.

## Implementation plan

1. Finalize the guest capability matrix in docs and mirror it in the public
   Klassrumskartan host behavior.
2. Extend the public host and guest workspace seams so rosters, templates,
   smart rules, and drafts stay browser-owned and honest in public mode.
3. Reuse or extend the public helper namespace only for stateless import
   preview and smart compute flows.
4. Keep guest export as direct download and explicitly block/signpost
   account-owned export recovery and adjacent authenticated-only affordances.
5. Add the `Rensa arbetsyta` affordance and confirmation copy in the guest
   shell without surfacing internal storage terminology.
6. Prove unchanged authenticated behavior plus guest/reset/export/first-auth
   upgrade flows with focused browser verification.

## Test plan

- `pdm run precommit-run`
- `pnpm -C frontend --filter @skriptoteket/spa exec vitest run`
- `pdm run docs-validate`
- focused browser proof for:
  - guest authoring continuity
  - `Rensa arbetsyta`
  - direct-download guest export
  - first authenticated Klassrumskartan visit prompting upgrade
  - unchanged authenticated Klassrumskartan host behavior after upgrade or when
    no guest state exists

## Rollback plan

Revert only the public Klassrumskartan demo-adoption behavior in this slice and
restore the prior public-host surface while keeping the already-shipped
browser-owned guest snapshot and authenticated upgrade foundations intact.
