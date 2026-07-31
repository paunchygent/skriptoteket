---
type: reference
id: REF-SKRIPT-GENERAL-product-context
title: Product context
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: draft
reference_kind: general
links:
  references:
    - REF-current-product-direction-and-backlog-inventory-2026-06-17
    - REF-hule-education-product-identity-realms-and-skriptoteket-standalone-identity
    - REF-huleedu-launch-surface-and-shared-auth-topology-2026-04-08
    - REF-current-product-lanes-and-sir-convert-boundary-v1
    - REF-public-landing-copy-lock
summary: 'Durable product context for Skriptoteket: mission, identity, current aim,
  non-goals, load-bearing decisions, constraints, and glossary for external architect
  agents.'
---

## Overview

This reference is the durable product-context entry point for Skriptoteket. It
states the mission, product identity, current aim, boundaries, load-bearing
decisions, constraints, and vocabulary — the rationale layer that cannot be
recovered from code.

Primary consumers are external architect agents (the product owner's
lead-architect assistant reading through the read-only repository service) and
fresh agent sessions that need product grounding before planning. Read order:
the cross-repository portfolio context manifest in the skill repository — a
pending draft under its governing task `TASK-SKILL-REP-0060`, intended
canonical path
`docs/reference/ref-skill-general-portfolio-context-manifest.md` there — then
this reference, then the routed PRDs, ADRs, and backlog items linked below.

Last reconciled: 2026-07-31, against `.codex/handoff.md` (2026-07-31), the
EPIC-37/EPIC-38 backlog state, and
`docs/reference/ref-current-product-direction-and-backlog-inventory-2026-06-17.md`.
If ADR acceptances, PRD version changes, or epic transitions postdate that
date, treat the "Current aim" section as potentially stale and verify against
the backlog before relying on it.

## Facts And Semantics

### Mission and problem

Skriptoteket is a teacher-first web service for Swedish school staff. Teachers
log in, open a curated app or catalog tool in the browser, feed it their
files, and download results. It removes repetitive preparation work — seating
and grouping plans, speech transcription, exam conversion and correction,
document conversion — without local installs, scripting skill, or sending
school data through arbitrary third parties.

The product began as a "Script Hub" (a governed catalog of Python tools) and
is now a teacher-first productivity service built around bespoke application
lanes; script authoring and execution remain a preserved substrate, no longer
the only front-door story per the
[current product-direction memo](ref-current-product-direction-and-backlog-inventory-2026-06-17.md).

Audiences:

- Teachers, as authenticated users and as anonymous guests for open curated
  apps (Klassrumskartan works without an account; production Swedish landing
  copy is frozen in the
  [public landing copy lock](ref-public-landing-copy-lock.md)).
- Teacher-authors and admins who create and govern tools (the
  [teacher-developer guide](../../stakeholders/guide-teacher-developers.md)
  and the [tool-authoring PRD](../prd/prd-tool-authoring-v0.1.md)).
- Municipal IT organizations as prospective self-hosters; the repo is built to
  be forked and adapted to local constraints (on-prem, VPN-only, approved SMTP
  relays, strict retention).

### Product identity

Hule Education owns the browser edge — session cookies, CSRF, the login
ceremony, and Gateway-signed downstream identity context — but not
Skriptoteket account meaning. Skriptoteket is a distinct product identity
realm (`skriptoteket_standalone`) alongside `huleedu_school`: a user can hold
a Skriptoteket account without ever registering for the HuleEdu school
product, and realm linking is explicit only. Skriptoteket keeps app-local
identity projections, profiles, AI preferences, and RBAC (`user`,
`contributor`, `admin`, `superuser` are local promotions).

Authorities:
[ADR-0083 product identity realms](../adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md)
(accepted), the
[identity-realms reference](ref-hule-education-product-identity-realms-and-skriptoteket-standalone-identity.md),
and the
[launch-surface and shared-auth topology reference](ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md).

### Deployment reality and constraints

- `skriptoteket.hule.education` is the real live app host with real users;
  this is a running public service, not a prototype.
- Production runs on the shared Hemma host: PostgreSQL 16 in the shared
  `shared-postgres` container on the `hule-network` Docker bridge, behind the
  nginx-proxy + acme-companion edge, co-tenant with HuleEdu and Sir
  Convert-a-Lot. Use the
  [launch-surface and shared-auth topology reference](ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md)
  as the current host-topology authority.
- Protected browser API traffic enters only through the HuleEdu Gateway at
  `https://api.hule.education/api/...`; direct protected calls to the app host
  are Gateway-bypass defects. Public `/api/v1/public/...` routes stay on the
  Skriptoteket backend.
- Municipal self-host adaptability is a first-class constraint: air-gap LLM
  switch, pluggable SMTP relay, `ARTIFACTS_ROOT` retention, optional separate
  runner host, `/metrics` and `/healthz` surfaces (`README.md`).
- Remote LLM providers are gated by `AI_REMOTE_PROVIDERS_ENABLED` plus
  per-user opt-in; NULL counts as deny.
- Single-operator reality (product-owner-supplied fact, recorded here as
  context for external advisers): one person owns product direction, code, and
  operations. Prefer solutions that one person can build, run, and repair;
  distrust proposals that assume a team.

### Glossary

- Skriptoteket: the product — a teacher-first web service for Swedish school
  staff, self-hostable, centred on bespoke teacher app lanes.
- Klassrumskartan: the flagship curated app
  (`classroom.group-seating-studio`) for class-first seating and grouping
  planning; class is the anchor, seating and grouping are separate drafts.
- Script hub: the original product shape and still the platform substrate — a
  governed catalog of Python tools browsed by profession and category.
- Curated apps: owner-authored first-class application modules with bespoke
  UX and app-specific APIs, discovered through a shipped registry
  ([ADR-0023](../adr/adr-0023-curated-apps-registry-and-execution.md)).
- Tool authoring: the admin/contributor path for creating, reviewing, and
  publishing tools
  ([tool-authoring PRD](../prd/prd-tool-authoring-v0.1.md)).
- Editor sandbox: the author-side iteration surface for running unsaved tool
  snapshots safely
  ([editor-sandbox PRD](../prd/prd-editor-sandbox-v0.1.md)).
- Product identity realms: distinct account namespaces (`huleedu_school`,
  `skriptoteket_standalone`) behind one shared Hule Education login ceremony.
- Sir Convert-a-Lot: the sibling producer service owning heavy conversion,
  OCR, and hosted model/STT runtime; Skriptoteket owns native product state
  after conversion per the
  [product-lanes and Sir Convert boundary reference](ref-current-product-lanes-and-sir-convert-boundary-v1.md).
- Mina filer: the durable teacher-owned file vault addressed by `vault:*`
  FileRefs.

### Routing

- Current PRDs:
  [Klassrumskartan v0.3](../prd/prd-group-seating-studio-v0.3.md) (active),
  [SPA frontend v0.1](../prd/prd-spa-frontend-v0.1.md) (active),
  [editor sandbox v0.1](../prd/prd-editor-sandbox-v0.1.md) (active),
  [script hub v0.2](../prd/prd-script-hub-v0.2.md) (draft),
  [tool authoring v0.1](../prd/prd-tool-authoring-v0.1.md) (draft).
- Direction memos:
  [product direction and backlog inventory](ref-current-product-direction-and-backlog-inventory-2026-06-17.md),
  [product lanes and Sir Convert boundary](ref-current-product-lanes-and-sir-convert-boundary-v1.md),
  [service-shell UX realignment plan](ref-service-shell-ux-realignment-plan-v1.md).
- Backlog: `docs/backlog/{epics,stories,prs,reviews}/`, hierarchy
  `EPIC -> STORY -> PR slice`; volatile state in `.codex/handoff.md`.
- Docs contract and validation: `docs/_meta/docs-contract.yaml`,
  `pdm run docs-validate`.

## Decisions And Interpretation

### Current aim

Reconciled 2026-07-31.

Now, in flight:

- EPIC-37 (active) is the live product spine: backlog product-direction
  inventory and app-surface realignment. The Document Converter chain under
  ST-37-04 is delivered through its remediation slices; ST-37-05 cross-app
  save/export file naming is the next queued product contract (PR-0390 ready).
- ST-14-39 Mina filer storage migration to Cloudflare R2: PR-0412 in
  progress; ADR-0088 still proposed.
- EPIC-21 Conversion Hub / Exam Converter (active): correction and
  design-alignment slices done.
- EPIC-38 shared governed development-system cutover is developer tooling,
  not product direction. The approved central review under Skill Repository
  `ST-SKILL-08-06` plus a user exception authorized the serialized PR-0417
  direct-main bootstrap; the remaining slices are gated on the PR-0418
  current-corpus migration.

Next, open lanes: EPIC-27 Klassrumskartan smart assignment v1, EPIC-29
desktop-first workspace overhaul, EPIC-26 explicit exports and class-list
import, EPIC-36 scoped sharing and authenticated import (proposed), EPIC-35
launch SEO readiness, EPIC-09 security hardening, and the game lanes (EPIC-25,
EPIC-33, EPIC-31). Dormant: EPIC-20 Reagent Prep Chef, EPIC-22 textbook corpus
RAG readiness.

### Non-goals and rejected directions

- Server-rendered HTMX UI: superseded by the full Vue/Vite SPA as a clean
  break; no dual SSR/SPA support
  ([ADR-0027](../adr/adr-0027-full-vue-vite-spa.md)).
- App-local browser sessions, CSRF, password collection, or browser-minted
  identity headers: forbidden; HuleEdu owns the browser edge (`README.md`,
  [ADR-0076](../adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md)).
- A HuleEdu-only identity future: rejected; the standalone realm exists so
  Skriptoteket users never need the HuleEdu school product
  ([ADR-0083](../adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md)).
- Kafka / event streaming: deferred until durable async fan-out is actually
  needed ([ADR-0007](../adr/adr-0007-defer-kafka-until-needed.md)).
- Arbitrary tool-provided JavaScript in the UI: interactivity comes only from
  platform-rendered allowlisted components
  ([ADR-0022](../adr/adr-0022-tool-ui-contract-v2.md)).
- Offline mode / PWA and a second admin SPA: PRD non-goals
  ([SPA frontend PRD](../prd/prd-spa-frontend-v0.1.md)).
- Solver/optimizer language in the default teacher UI: the manual happy path
  stays simple
  ([Klassrumskartan PRD](../prd/prd-group-seating-studio-v0.3.md)).
- Sir Convert replay/fingerprint/artifact-overlay machinery for native app
  state: reserved for producer-owned heavy-conversion evidence only
  ([product-lanes reference](ref-current-product-lanes-and-sir-convert-boundary-v1.md)).
- Scrapping the script editor/runner because bespoke apps are now the front
  door: explicitly out of scope in EPIC-37 — "no longer front-door
  positioning" is distinct from "no longer valuable".
- Remote LLM providers by default: gated and opt-in only.

### Load-bearing decisions

- [ADR-0004](../adr/adr-0004-clean-architecture-ddd-di.md) (accepted): DDD +
  Clean Architecture with protocol-first DI; domain imports no FastAPI/DB.
- [ADR-0002](../adr/adr-0002-backend-fastapi.md) (accepted): FastAPI
  monolith.
- [ADR-0027](../adr/adr-0027-full-vue-vite-spa.md) (accepted): one Vue 3/Vite
  SPA for the whole surface, served same-origin by FastAPI.
- [ADR-0022](../adr/adr-0022-tool-ui-contract-v2.md) (accepted): typed UI
  contract — runs return `outputs[]`, `next_actions[]`, persisted `state`;
  the platform renders, tools ship no JS.
- [ADR-0023](../adr/adr-0023-curated-apps-registry-and-execution.md)
  (accepted): curated apps as a first-class subject kind with a shipped
  registry.
- [ADR-0013](../adr/adr-0013-execution-ephemeral-docker.md) (proposed):
  sandboxed sibling runner containers — `network_mode=none`, `cap_drop=ALL`,
  read-only root, resource limits.
- [ADR-0062](../adr/adr-0062-execution-queue-and-worker-loop.md) (accepted):
  durable Postgres job queue with leases/retries; queue-backed execution is
  default.
- [ADR-0076](../adr/adr-0076-huleedu-owned-browser-session-authority-for-skriptoteket.md)
  (proposed): HuleEdu Identity as sole browser session authority — the
  decision EPIC-28 (done) implemented.
- [ADR-0083](../adr/adr-0083-hule-education-product-identity-realms-for-skriptoteket-login.md)
  (accepted): product identity realms with fail-closed provisioning and
  explicit-only linking.
- [ADR-0082](../adr/adr-0082-app-local-bootstrap-continuation-on-huleedu-session.md)
  (accepted): app-local continuation on a HuleEdu-owned session.
- [ADR-0079](../adr/adr-0079-public-curated-app-access-profiles-and-guest-state-boundaries.md)
  (accepted, amended by ADR-0085): public curated-app access under declared
  profiles with bounded guest state.
- [ADR-0081](../adr/adr-0081-hemma-deploy-entrypoint-and-script-first-local-launcher.md)
  (accepted): the on-host script is the only deploy logic.
- [ADR-0072](../adr/adr-0072-group-seating-studio-class-first-workspace-and-draft-kinds.md)
  (accepted): Klassrumskartan's class-first, one-active-draft-per-kind model.
- [ADR-0005](../adr/adr-0005-user-roles-and-script-governance.md) (accepted):
  four-role RBAC and the suggest -> review -> publish governance chain.

### Known metadata drift

Several implemented, production-depended decisions still carry `proposed`
front-matter: ADR-0013 (runner sandbox), ADR-0076 (browser-session cutover),
ADR-0053 (production security perimeter), ADR-0066 (Sir Convert v2 engine),
ADR-0088 (R2 storage), ADR-0035 (editor intelligence). External reviewers must
not read `proposed` status alone as "not implemented"; verify against code and
backlog state. The
[home-server architecture reference](ref-home-server-architecture.md)
host-fallback claims are superseded by the
[launch-surface and shared-auth topology reference](ref-huleedu-launch-surface-and-shared-auth-topology-2026-04-08.md).

### Reconciliation rule

Update this reference — and its "Last reconciled" line — whenever an ADR is
accepted or superseded, a PRD version becomes active, an epic opens or closes,
or a product-direction memo lands. Governing task:
[TASK-SKRIPT-REP-0001](../backlog/tasks/task-skript-rep-0001-publish-product-context-reference-for-external-architect-agents.md).
