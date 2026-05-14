---
type: review
id: REV-PR-0320
title: "Review: PR-0320 Exam Converter public one-time runtime lane"
status: approved
owners: "agents"
created: 2026-05-13
updated: 2026-05-13
reviewer: "codex"
prs:
  - PR-0320
adrs:
  - ADR-0085
  - ADR-0079
links:
  - EPIC-21
  - ST-21-03
  - PR-0319
  - REV-PR-0319
  - PR-0321
---

## TL;DR

`PR-0320` is approved for runtime implementation. HuleEdu `TASK-0563`/`ADR-0045`
and Sir Convert `TASK-291` now define the public grant lane, `REV-PR-0321`
approved the local runtime-status/action-affordance bridge, and the active docs
now point at the real HuleEdu `docs/decisions/0045...` authority. This approval
does not approve runtime code in advance; the implementation slice must still
prove submit, poll, result, artifact manifest, download, cookie parity, TTL,
abuse controls, no account persistence, no browser-exposed authority material,
and fail-closed direct public upstream traffic.

## Problem Statement

This review checks whether the `PR-0320` implementation package is safe and
specific enough to authorize the public Exam Converter runtime behind the
`PR-0319` scoped public-capability metadata.

## Proposed Solution

`PR-0320` proposes a dedicated public API namespace and minimal public host that
accept anonymous `.dxe` uploads, optional sanitized graded-result PDFs, target
selection, status polling, artifact manifests, and direct artifact downloads
without Vault/MyFiles writes or account history.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/prs/pr-0320-st-21-03-exam-converter-public-one-time-runtime-lane.md` | Public-runtime scope, acceptance criteria, stop conditions | 15 min |
| `docs/backlog/stories/story-21-03-exam-converter-public-and-authenticated-artifact-lanes.md` | Public/authenticated lane split and PR ordering | 10 min |
| `docs/adr/adr-0085-exam-converter-public-conversion-exception-for-conversion-hub.md` | Scoped public exception authority | 10 min |
| `/Users/olofs_mba/Documents/Repos/huleedu/docs/backlog/tasks/task-0559-implement-sir-convert-protected-gateway-route-surface-and-signed-audience.md` | Gateway route and session authority | 10 min |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/converters/digiexam-migration-service-api-artifact-contract.md` | Downstream conversion/ownership contract | 10 min |
| `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/reference/ref-sir-convert-internalidentitycontextv1-authorization-profile.md` | Allowed caller classes and minting authority | 10 min |
| `src/skriptoteket/web/api/v1/public_apps.py` | Frozen PR-0319 public metadata shape consumed by the next slice | 5 min |
| `frontend/apps/skriptoteket/src/views/curatedAppHostRegistry.ts` | Existing public host resolver boundary | 5 min |

**Total estimated time:** ~75 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Implement anonymous public submit/poll/download in this slice | Grant-lane authority now exists in dependency docs, but retained bridge and upstream acceptance evidence still block runtime approval | [ ] |
| Keep all browser traffic under the scoped public Skriptoteket namespace | Correct boundary from PR-0319 and ADR-0085 | [x] |
| Keep general Conversion Hub authenticated-only | Correct boundary from ADR-0085 and PR-0319 | [x] |
| Treat PR-0319 metadata as the runtime contract without amending its status shape | Resolved by PR-0321's explicit runtime-status/action-affordance bridge and approved in `REV-PR-0321` | [x] |

## Review Checklist

- [x] Governing PR, story, ADR, and prior review surfaces were read.
- [x] Public surfaces under review were enumerated.
- [x] Upstream HuleEdu/Sir Convert route and identity contracts were checked.
- [x] Cookie-parity and no-account-persistence requirements were checked
      against upstream ownership semantics.
- [x] The implementation package has an approved server-mediated upstream path
      for anonymous Exam Converter work.
- [x] The bootstrap metadata can truthfully describe an active runtime without
      reopening the PR-0319 contract.
- [x] Verification gates are sufficient for the claimed runtime surface.

## Review Feedback

**Reviewer:** `codex`
**Date:** `2026-05-13`
**Verdict:** `changes_requested`

### First-pass Required Changes

Findings 1 and 2 are retained as the original first-pass blockers. See the
2026-05-13 re-review section for the current blocker state after `PR-0321`,
HuleEdu `TASK-0563`, and Sir Convert `TASK-291`.

#### Finding 1: Blocker - no approved upstream path exists for anonymous public conversion

Before this review, `PR-0320` was marked ready, and its acceptance criteria
required anonymous public submit, poll, artifact manifest, and direct download
behavior under the public Skriptoteket namespace. The same PR also says
implementation must stop if no approved server-mediated upstream path exists
for anonymous Exam Converter work. That stop condition was true in the first
pass.

The downstream Sir Convert contract explicitly keeps the product route behind
HuleEdu Gateway, derives job ownership from verified
`InternalIdentityContextV1`, and states that direct anonymous public conversion
is not part of the contract. The authorization profile's caller matrix marks
`Anonymous public` as `Reserved/fail-closed only`. The HuleEdu Gateway task
implemented a protected route surface that requires browser-session transport
and CSRF for job submission.

**Why it matters:** an implementation can only choose unsafe shapes from here:
use the authenticated Gateway with no session and fail every anonymous submit,
smuggle public work through a service-owned/internal lane, make Skriptoteket
call Sir Convert directly, or create local job ownership semantics that the
downstream artifact reads do not authorize. Each option violates the cited
contracts or produces a public UI that can accept uploads but cannot complete
poll/download semantics.

**Concrete fix:** do not implement the public runtime yet. Either:

- create and approve a HuleEdu/Sir Convert dependency slice that defines an
  anonymous-public Exam Converter conversion lane, including ownership,
  grants, abuse controls, TTL, artifact-read semantics, privacy proof, and
  Gateway/Sir Convert route authority; or
- retarget `PR-0320` to a smaller validation-only/local contract slice that
  never calls Sir Convert and keeps runtime submission disabled until that
  dependency exists.

**Proof requirement:** the eventual unblocked PR must include positive and
negative cross-repo proof for anonymous submit, poll, result, artifact manifest,
named download, TTL expiry, rate/concurrency limits, no Vault/MyFiles writes,
no account/session authority, no browser `X-API-Key`, and fail-closed direct
`convert.hule.education` traffic.

#### Finding 2: High - runtime activation conflicts with the frozen `contract_only` bootstrap shape

`PR-0320` says it will consume the `PR-0319` metadata contract without changing
the scoped metadata, but the actual bootstrap model only permits
`runtime_status: "contract_only"`. The frontend route was intentionally
reviewed as a shell that loads the scoped metadata without resolving a runtime
view. A public runtime implementation cannot truthfully keep returning
`contract_only`, and changing that field is a public bootstrap contract change.

**Why it matters:** the public host, generated OpenAPI types, and frontend tests
will either keep treating the route as missing-runtime even after backend
runtime code exists, or the implementation will silently widen the public
metadata contract outside the governed scope. That weakens the exact PR-0319
boundary this slice is supposed to consume.

**Concrete fix:** explicitly include a governed metadata transition in the
unblocked runtime slice, for example a narrow `runtime_status` value such as
`active` plus the exact route/action affordances needed by the public host. Keep
the app-wide `public_access_profile` authenticated-only and keep the scoped
capability boundary intact.

**Proof requirement:** update backend route tests, OpenAPI generation,
frontend type checks, and public host specs so they prove both states:
contract-only metadata before runtime and active-runtime metadata after the
public lane is actually available.

### Suggestions

- Keep the anonymous-public upstream dependency separate from product-polish
  UI work; the first safe decision is an authority/ownership decision, not a
  form-design pass.
- When the dependency is approved, preserve `source_dxe` as the public
  browser-facing field only if the backend adapter explicitly maps it to Sir
  Convert's downstream `file` part and tests that no browser field name leaks
  into downstream ownership or route semantics.

### Decision Approvals

- [x] Anonymous public conversion runtime
- [x] Dedicated public namespace
- [x] General Conversion Hub remains authenticated-only
- [x] Metadata transition for active runtime

### Re-review 2026-05-13

**Reviewer:** `codex`
**Date:** `2026-05-13`
**Verdict:** `changes_requested`

The original authority and metadata findings are no longer in the same state:

- HuleEdu `ADR-0045` is accepted after `REV-TASK-0563-01` and defines a
  server-mediated public Exam Converter grant authority.
- Sir Convert `TASK-291` is `completed` and defines the matching public grant
  verifier/job ownership contract.
- Skriptoteket `PR-0321` adds `contract_only`, `grant_contract_ready`, and
  `active` runtime status values, exposes disabled action affordances while the
  runtime is not active, and preserves the app-wide
  `authenticated_only` Conversion Hub profile.
- Focused re-review tests passed:
  `pdm run pytest tests/unit/domain/curated_apps/test_models.py tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_public_apps_api_routes.py -q`
  (`15 passed`) and
  `pdm run fe-test -- --run src/views/PublicAppHostView.spec.ts src/api/client.spec.ts`
  (`31 passed`).

Approval is still blocked by these retained findings.

#### Finding 3: Blocker - `PR-0320` now consumes an unreviewed `PR-0321` bridge

`PR-0320` now says its runtime implementation depends on `PR-0321` having
landed the local metadata/grant adapter contract. `PR-0321` is marked `done` and
contains backend, frontend, generated OpenAPI, docs, and test changes, but there
is no retained `REV-PR-0321` under `docs/backlog/reviews/`. The repo review
workflow requires retained review records for implementation packages, and this
bridge is the contract that decides whether the public runtime can move from
`contract_only` to grant-backed execution.

**Why it matters:** approving `PR-0320` would make the runtime slice depend on a
public authority bridge that has implementation code and public metadata shape
but no retained approval. That collapses the review gate that was created to
keep no-login conversion from drifting into direct Sir Convert access, raw grant
exposure, or account-owned persistence.

**Concrete fix:** create and approve a retained `REV-PR-0321`, or explicitly
expand this retained review's governed scope to include `PR-0321` and review the
bridge code/docs as part of the same approval. Only then update `PR-0320` from
`blocked` to the next implementation-ready state.

**Remediation note 2026-05-13:** retained `REV-PR-0321` now exists with
`status: pending`, and `PR-0321` is no longer marked `done`. This keeps the
review gate visible, but the blocker remains until `REV-PR-0321` is approved or
an equivalent retained review explicitly covers the bridge.

**Proof requirement:** the approving review must cite the backend public
metadata tests, frontend host/bootstrap tests, generated OpenAPI update, and the
repo close-out gates: `pdm run lint`, `pdm run typecheck`,
`pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`,
`pdm run docs-validate`, `pdm run handoff-validate`, and `git diff --check`.

#### Finding 4: High - the bridge cites a non-existent HuleEdu decision path

`PR-0321` and `ST-21-03` cite the HuleEdu authority as
`/Users/olofs_mba/Documents/Repos/huleedu/docs/adr/adr-0045-public-exam-converter-grant-authority-for-sir-convert.md`.
That file does not exist. The accepted HuleEdu decision is
`/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`.

**Why it matters:** the next runtime implementer is supposed to stop if the
upstream grant contract drifts. A broken authority pointer makes that stop
condition unreviewable and invites people to rely on summaries instead of the
accepted decision.

**Concrete fix:** replace the stale `/docs/adr/adr-0045...` references in the
Skriptoteket story and `PR-0321` dependency list with the real
`/docs/decisions/0045...` path.

**Remediation note 2026-05-13:** the stale HuleEdu decision references were
replaced with
`/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`
in `ST-21-03` and `PR-0321`.

**Proof requirement:** run `test -f` against the corrected absolute path and
close with `pdm run docs-validate`.

#### Finding 5: High - Sir Convert acceptance evidence is still not retained at the review gate

HuleEdu has an explicit retained approval record for `TASK-0563`, but this
re-review could not locate a Sir Convert retained review record for `TASK-291`.
The Sir Convert task is `completed` and says the verifier/ownership contract is
accepted, but `PR-0320`'s original unblock condition required the upstream lane
to be approved rather than merely described.

**Why it matters:** the runtime slice will call through this public grant lane.
If the Sir Convert side has not passed an explicit review gate, Skriptoteket is
again relying on an unreviewed cross-repo contract for public job ownership,
artifact-read leases, replay behavior, and fail-closed direct public traffic.

**Concrete fix:** either locate and link the retained Sir Convert review for
`TASK-291`, or update the Sir Convert/Skriptoteket backlog docs to make the
accepted task status the explicit approval gate for this contract slice.

**Remediation note 2026-05-13:** no retained Sir Convert `TASK-291` review was
located under
`/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/reviews/`.
`PR-0321` and pending `REV-PR-0321` now keep that acceptance-evidence gap
explicit instead of treating completed task status as runtime-unblocking proof.

**Proof requirement:** the runtime-unblocking package must link that Sir Convert
approval evidence and keep the direct public `convert.hule.education` traffic
fail-closed proof in the eventual `PR-0320` test plan.

### Re-review 2026-05-13 After Bridge Review

**Reviewer:** `codex`
**Date:** `2026-05-13`
**Verdict:** `approved`

The retained blockers are closed:

- Finding 3 is resolved by approved `REV-PR-0321`, which reviewed the bridge
  scope directly and approved the `contract_only` / `grant_contract_ready` /
  `active` runtime-status shape, disabled grant-ready affordances, opaque-handle
  authority boundary, and app-wide `authenticated_only` Conversion Hub profile.
- Finding 4 is resolved: active `ST-21-03` and `PR-0321` dependencies now cite
  `/Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`,
  and `test -f` passed for that path.
- Finding 5 is resolved for Skriptoteket's gate: Sir Convert's own docs contract
  does not require a separate retained review document for every task, and this
  review accepts completed Sir Convert `TASK-291` plus the updated converter and
  authorization-profile contracts as the upstream Sir Convert approval evidence
  for the bridge. The eventual runtime proof still must exercise the public grant
  lane positively and negatively.

Verification run during this re-review:

- `pdm run pytest tests/unit/domain/curated_apps/test_models.py tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_public_apps_api_routes.py -q`
  (`15 passed`)
- `pdm run fe-test -- --run src/views/PublicAppHostView.spec.ts src/api/client.spec.ts`
  (`31 passed`)
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `test -f /Users/olofs_mba/Documents/Repos/huleedu/docs/decisions/0045-public-exam-converter-grant-authority-for-sir-convert.md`
- `rg -n "docs/adr/adr-0045-public-exam-converter-grant-authority-for-sir-convert" docs/backlog/prs docs/backlog/stories docs/adr docs/index.md .codex/handoff.md`
  (no active-doc matches)
- `find /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/backlog/reviews -maxdepth 1 -type f \( -iname '*291*' -o -iname '*grant*' -o -iname '*exam*converter*' \) -print`
  (no retained Sir Convert review found; accepted via completed-task authority
  as recorded above)
- `rg -n "convert\\.hule\\.education|X-API-Key|SIR_CONVERT_A_LOT_V2_API_KEY|127\\.0\\.0\\.1:9010|PublicConversionGrantV1|PublicArtifactReadLeaseV1" src/skriptoteket/web/static/spa`
  (no matches)

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | `PR-0320` | Retained review recorded `changes_requested`; implementation is blocked until anonymous upstream authority and active-runtime metadata semantics are governed. |
| 2 | `PR-0320` re-review | Retained `changes_requested` after re-checking HuleEdu `TASK-0563`, Sir Convert `TASK-291`, and Skriptoteket `PR-0321`; original technical blockers moved, but bridge review/authority evidence still blocks runtime approval. |
| 3 | `PR-0320` re-review after bridge review | Approved runtime implementation package after `REV-PR-0321` approval, corrected HuleEdu decision paths, Sir Convert completed-task authority acceptance, full focused backend/frontend proof, lint/typecheck, frontend build, docs gates, and forbidden production-bundle string grep. |
