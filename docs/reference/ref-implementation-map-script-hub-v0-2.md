---
type: reference
id: REF-implementation-map-script-hub-v0-2
title: "Implementation map: Script Hub v0.2 roadmap (sessions + checkpoints)"
status: active
owners: "agents"
created: 2025-12-19
updated: 2025-12-21
topic: "implementation-roadmap"
links:
  - "PRD-script-hub-v0.2"
  - "EPIC-10"
  - "ADR-0022"
  - "ADR-0023"
  - "ADR-0024"
  - "ADR-0027"
  - "SPR-2025-12-22"
  - "SPR-2026-01-06"
  - "SPR-2026-01-20"
  - "SPR-2026-02-03"
  - "SPR-2026-02-17"
---

This document maps the v0.2 initiative into an implementation route with session-sized targets, checkpoints, and
concrete success criteria. It is intended for the developer/agent doing the work.

Status note: Skriptoteket’s UI paradigm has been superseded by ADR-0027 (full SPA). Any SSR/HTMX-default or SPA-islands
language in this document is historical and should not be used as a guardrail for new work.

The planning source of truth is:

- PRD: `docs/prd/prd-script-hub-v0.2.md`
- ADRs: `docs/adr/adr-0022-tool-ui-contract-v2.md`, `docs/adr/adr-0023-curated-apps-registry-and-execution.md`,
  `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md`, `docs/adr/adr-0027-full-vue-vite-spa.md`
- Epic: `docs/backlog/epics/epic-10-interactive-ui-contract-and-curated-apps.md`
- Sprints: `docs/backlog/sprints/`

## Global implementation guardrails

Non-negotiables for all sessions:

- Protocol-first DI (depend on protocols, not concrete implementations).
- Deterministic normalization: same input + policy → byte-identical stored `ui_payload`.
- No arbitrary tool-provided UI JS; HTML remains sandboxed.
- UI paradigm: full SPA (ADR-0027). Avoid introducing new SSR/HTMX surfaces.

Always run:

- `pdm run docs-validate` after doc edits.
- `pdm run test` (or targeted tests) after implementation sessions.

Session rule reminder:

- Any session that changes UI/routes MUST include a live functional check and a `.agent/handoff.md` note describing how
  it was verified.

## Roadmap overview (by sprint)

1. **SPR-2025-12-22** (2025-12-22 → 2026-01-05): contract v2 + persistence + normalizer (ST-10-01..03)
2. **SPR-2026-01-06** (2026-01-06 → 2026-01-19): interactive API + curated apps MVP (ST-10-04..06)
3. **SPR-2026-01-20** (2026-01-20 → 2026-02-02): SSR rendering for typed UI (ST-10-07)
4. **SPR-2026-02-03** (2026-02-03 → 2026-02-16): SPA toolchain + editor island MVP (ST-10-08..09)
5. **SPR-2026-02-17** (2026-02-17 → 2026-03-02): runtime SPA island MVP (ST-10-10)

## Session breakdown

### Sprint SPR-2025-12-22 (Foundations)

**Session A — lock contracts + policy budgets**

- Target:
  - Accept ADR-0022 + ADR-0024 (or explicitly record remaining decision points).
  - Define the initial allowlists + size budgets for `default` vs `curated` UI policies.
- Concrete steps:
  1. Ensure contract v2 schema is represented as Pydantic models at the boundary (domain remains pure).
  2. Define policy model for budgets/allowlists (protocol: `UiPolicyProviderProtocol`).
  3. Add unit tests for policy selection and budget constants (no web dependencies).
- Checkpoints:
  - Unit tests prove budgets and allowlists are enforced for at least 2 output kinds.
  - Any undecided items are captured as follow-up stories (do not leave implicit TODOs).

**Session B — deterministic normalizer (pure + testable)**

- Target:
  - Implement `UiPayloadNormalizerProtocol` + initial implementation.
- Concrete steps:
  1. Implement canonicalization rules (ordering, truncation, notices).
  2. Enforce allowlists for output kinds and action field kinds.
  3. Prove determinism: normalize the same payload twice → identical JSON bytes (stable ordering).
- Checkpoints (success criteria):
  - ST-10-03: allowlist enforcement, size-budget truncation w/ notice, byte-identical determinism.
  - Test with: markdown + table + html_sandboxed.

**Session C — persistence schema + migrations**

- Target:
  - Add `tool_sessions` table and `tool_runs.ui_payload` JSONB.
- Concrete steps:
  1. Implement DB schema changes (Alembic migration).
  2. Add repository/UoW methods (protocol-first) to read/write sessions and persist `ui_payload`.
  3. Add tests for optimistic concurrency behavior at the application layer.
- Checkpoints (success criteria):
  - ST-10-02: state + state_rev increments; clear memory; stale `expected_state_rev` rejects.
  - ST-10-01/ST-10-03: persisted run includes validated `ui_payload`.

**Session D — runner/app contract v2 enforcement**

- Target:
  - Update runner output parsing to require `contract_version=2` and treat other versions as violations.
- Concrete steps:
  1. Update runner contract v2 emitter and app-side parser/validator.
  2. Ensure failure modes are user-safe (`error_summary`) and logged internally.
  3. Add contract tests for v2 parsing and v1 rejection.
- Checkpoints (success criteria):
  - ST-10-01: v2 required; other versions rejected as contract violation.

### Sprint SPR-2026-01-06 (API + curated apps)

**Session E — interactive API endpoints**

- Target:
  - Implement `start_action`, `get_session_state`, `get_run`, `list_artifacts` (ST-10-04).
- Concrete steps:
  1. Add API routes (thin web layer) + application handlers.
  2. Ensure optimistic concurrency via `expected_state_rev`.
  3. Ensure `get_run` always returns stored `ui_payload` (never raw runner payload).
- Checkpoints (success criteria):
  - ST-10-04 acceptance criteria pass via integration tests or targeted handler tests.

**Session F — curated registry seam**

- Target:
  - Implement `CuratedAppRegistryProtocol` + catalog integration (ST-10-05).
- Concrete steps:
  1. Define curated app metadata schema and registry location in the repo.
  2. Make curated apps discoverable in Katalog (role-gated) and non-editable in tool editor workflow.
- Checkpoints (success criteria):
  - ST-10-05 acceptance criteria pass (catalog shows curated apps; editor cannot edit them).

**Session G — curated execution seam**

- Target:
  - Implement `CuratedAppExecutorProtocol` and persist runs as `source_kind="curated_app"` (ST-10-06).
- Concrete steps:
  1. Implement executor that returns contract v2.
  2. Compose with backend action injection (protocol: `BackendActionProviderProtocol`).
  3. Run result through the same normalizer path and persist `ui_payload`.
- Checkpoints (success criteria):
  - ST-10-06 acceptance criteria pass; artifacts are handled with the same path safety rules.

### Sprint SPR-2026-01-20 (SSR typed UI rendering)

**Session H — SSR renderer MVP**

- Target:
  - Render stored `ui_payload.outputs[]` and `next_actions[]` in SSR pages (ST-10-07).
- Concrete steps:
  1. Add server-rendered components/templates per output kind.
  2. Ensure action forms submit to `start_action` with `expected_state_rev`.
  3. Keep `html_sandboxed` sandboxed without scripts.
- Checkpoints (success criteria):
  - Live functional check on an interactive tool page renders without SPA.
  - `.agent/handoff.md` records how the page was verified.

### Sprint SPR-2026-02-03 (SPA toolchain + editor island)

**Session I — Vite toolchain + asset integration**

- Target:
  - Establish SPA toolchain and manifest-based asset inclusion (ST-10-08).
- Concrete steps:
  1. Add `pnpm` workspace/app, Vite config, Tailwind setup aligned with HuleEdu.
  2. Implement prod hashed assets + manifest integration from Jinja templates.
  3. Implement dev workflow (dev server proxy or watch build).
- Checkpoints (success criteria):
  - Editor island page loads correct assets in both dev and prod modes.

**Session J — editor island MVP**

- Target:
  - Mount SPA island on admin/contributor editor pages and stabilize CodeMirror sizing (ST-10-09).
- Concrete steps:
  1. Implement minimal editor SPA that loads/saves editor content via backend API.
  2. Ensure HTMX coexistence rules (no swaps inside SPA root).
  3. Add frontend unit tests for the editor store/actions.
- Checkpoints (success criteria):
  - Live functional check: editor loads, edits, saves; no layout collapse.
  - `.agent/handoff.md` records verification.

### Sprint SPR-2026-02-17 (runtime island MVP)

**Session K — runtime island MVP**

- Target:
  - SPA island renders typed outputs and supports multi-turn actions (ST-10-10).
- Concrete steps:
  1. Implement runtime SPA that can fetch `get_run` + `get_session_state`.
  2. Submit actions via `start_action` and re-render updated `ui_payload`.
  3. Handle stale `expected_state_rev` with a refresh UX.
- Checkpoints (success criteria):
  - Live functional check: run → action → new run renders; reload preserves state.
  - `.agent/handoff.md` records verification.

## Release checkpoint (v0.2)

When the v0.2 scope is complete enough to ship:

- Create `docs/releases/release-script-hub-v0.2.md` from `docs/templates/template-release-notes.md`.
- Set `status: published` and add `released: YYYY-MM-DD`.
- Link the release notes to the shipped PRD/ADRs and the completed sprint(s).
