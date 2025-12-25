---
type: prd
id: PRD-script-hub-v0.1
title: "Script Hub PRD v0.1 (MVP)"
status: draft
owners: "agents"
created: 2025-12-13
updated: 2025-12-13
product: "script-hub"
version: "0.1"
---

## Summary

Build an internal “Script Hub” where staff run curated scripts via a simple web UI: choose a script, upload a file, get an HTML result (and sometimes a downloadable artifact).

## User Roles

1. **Users** (primary in v0.1): browse and run published scripts/tools.
2. **Contributors**: all user capabilities plus propose/suggest new scripts (and improvements) for review.
3. **Admins**: all contributor capabilities plus manage users/contributors and the script lifecycle (accept/modify/deny/publish/depublish); may propose new admins to the superuser.
4. **Superuser**: final authority; approves/denies new admin nominations and can change admin permissions.

## Governance & Script Lifecycle

### Lifecycle states

In v0.1, scripts/tools move through a small set of states:

- **Suggested**: created by a contributor as a proposal (not runnable by users).
- **Under review**: owned by an admin; can be edited/clarified.
- **Rejected**: admin denies the proposal (kept for traceability).
- **Accepted**: approved for implementation/publication; acceptance creates a **draft tool entry** (not runnable/published).
- **Published**: visible and runnable for users in the UI.
- **Depublished**: not visible/runnable for users (kept for rollback/audit).

### Admin promotion

- Admins can nominate new admins.
- The superuser approves/denies admin nominations.

## Permissions Matrix (v0.1)

| Capability | User | Contributor | Admin | Superuser |
|---|---:|---:|---:|---:|
| Browse and run published scripts | ✅ | ✅ | ✅ | ✅ |
| Suggest new scripts / improvements | ❌ | ✅ | ✅ | ✅ |
| View and triage suggestions | ❌ | ❌ | ✅ | ✅ |
| Accept / modify / deny suggestions | ❌ | ❌ | ✅ | ✅ |
| Publish / depublish scripts | ❌ | ❌ | ✅ | ✅ |
| Manage users / contributors | ❌ | ❌ | ✅ | ✅ |
| Nominate new admins | ❌ | ❌ | ✅ | ✅ |
| Approve/deny admin nominations | ❌ | ❌ | ❌ | ✅ |

## Identity & Authorization (MVP)

The identity subsystem must be minimal but robust:

- Authentication and “current user” resolution must be isolated behind protocols (testable via DI).
- Authorization checks are enforced at the interface layer (web/api), while application/domain logic relies on role/actor abstractions (no framework coupling).
- No self-signup and no external IdP/SSO in v0.1 by default; keep the design extensible for future SSO integration.
- Chosen v0.1 mechanism: **admin-provisioned local accounts + password auth + server-side sessions in PostgreSQL**.
- Access policy (v0.1): **browse/run requires login** (no anonymous catalog access).
- Future integration constraint: if/when HuleEdu SSO is added, Skriptoteket keeps **local roles** and stores `external_id` + `auth_provider` on users (ADR-0011).

## Findability (Taxonomy)

Scripts are grouped by:

- **Profession** (allowlist, expandable): `lärare`, `specialpedagog`, `skoladministratör`, `rektor`, `gemensamt`
- **Task-flow category** (allowlist, ordered per profession): `lektionsplanering`, `mentorskap`, `administration`, `övrigt`

Scripts may belong to **multiple** professions and categories.

## MVP Scope (v0.1)

- Browse: Profession → Category → Script list → Script page.
- Run: upload-based execution (csv/xlsx/docx/pdf/md/py-as-text) with clear errors.
- Server-driven UI with minimal JS (HTMX-style partial updates).
- Safety: **do not execute uploaded code**; treat uploads as untrusted input.

## Non-Goals (v0.1)

- Kafka/outbox/event streaming (introduce only when needed).
- Testcontainers-based DB testing (introduce after PostgreSQL repositories/models exist).
- Async job queue, multi-tenant auth, OCR for scanned PDFs, and executing user-uploaded Python.

## Success Metrics (initial)

- Time-to-first-result for common scripts: < 5 seconds (local / normal load, non-LLM).
- Successful runs on valid inputs: > 95%.
- New script to runnable (author workflow): < 30 minutes.

## Links

- Tool authoring (admin quick-create + slug lifecycle): `docs/prd/prd-tool-authoring-v0.1.md`
- ADR: tool slug lifecycle: `docs/adr/adr-0037-tool-slug-lifecycle.md`
- Epic: admin tool authoring: `docs/backlog/epics/epic-14-admin-tool-authoring.md`
