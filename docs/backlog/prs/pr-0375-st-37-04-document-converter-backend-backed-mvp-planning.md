---
type: pr
id: PR-0375
title: "ST-37-04 Document Converter backend-backed MVP planning"
status: ready
owners: "agents"
created: 2026-06-23
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - planning
  - document-converter
  - sir-convert
dependencies:
  - "PR-0368"
  - "PR-0374"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given Document Converter is an approved product lane but has no truthful runtime, when this planning slice closes, then it defines the backend-backed MVP contract before any route, host, registry capability, or runtime link is implemented."
  - "Given Sir Convert owns heavy format conversion, when the MVP is planned, then the plan inventories required Sir Convert routes, artifacts, accepted inputs, output targets, polling, download, save, and replay semantics."
  - "Given Exam Converter and Audio Transcription now have separate identities, when Document Converter is planned, then the plan keeps document conversion separate from exam creation/migration and audio transcription workflows."
  - "Given auth-edge behavior is sensitive, when implementation follow-ups are proposed, then they preserve HuleEdu Gateway browser-session, CSRF, signed identity, route grants, server-side Sir key injection, polling, replay, and artifact-download proof requirements."
---

# PR-0375: ST-37-04 Document Converter Backend-Backed MVP Planning

## Problem

Document Converter is now a visible future product lane, but it still has no
truthful backend-backed workflow in Skriptoteket. `PR-0368` and `PR-0374`
removed the misleading combined Conversion Hub presentation for Exam Converter
and Audio Transcription, which leaves Document Converter correctly inert but
still unplanned as a runnable app.

Implementing a route or shell before the producer/backend contract is reviewed
would recreate the same facade problem this story is removing.

## Goal

Create a planning package for a real Document Converter MVP that defines the
minimum truthful backend, Sir Convert, authenticated shell, artifact, export,
and save contract before any product route or registry capability is activated.

## Non-goals

- No Document Converter route, alias, host, runtime link, public capability, or
  registry activation in this slice.
- No reuse of Exam Converter or Audio Transcription presentation as a document
  conversion facade.
- No backend/API decomposition unless the planning artifact proves a concrete
  contract need and creates a later reviewed implementation slice.
- No HuleEdu Gateway, Sir Convert authentication, browser-session, CSRF,
  signed-identity, or route-grant change.
- No browser-authored identity headers, direct cookies, credential POST
  shortcuts, host-only backend proof, browser-direct Sir Convert calls, or
  browser-held Sir Convert credentials.

## Review gate

`REV-PR-0375` must approve the planning package before any Document Converter
implementation slice is created.

## Implementation plan

1. Inventory current Sir Convert document-format capabilities and Skriptoteket
   consumer surfaces for PDF, DOCX, HTML/CSS, Markdown, and template-shaped
   presentation outputs.
2. Define the MVP teacher workflow in product terms:
   source intake, target selection, conversion readiness, progress/polling,
   artifact review, download, Mina filer save, replay/retry, and failure
   recovery.
3. Define the contract split:
   Sir Convert producer responsibilities, HuleEdu Gateway auth-edge
   responsibilities, Skriptoteket backend state responsibilities, and frontend
   app-shell responsibilities.
4. Identify required backend/API surfaces, generated frontend types, app
   registry/capability changes, and any public route implications as separate
   follow-up slices.
5. Define red-first proof obligations for the first implementation slice,
   including focused backend contract tests, frontend route/host tests, and live
   shared-auth Docker plus Playwright proof.
6. Record stop conditions for any scope that drifts into exam migration, audio
   transcription, fake document routes, or auth-edge duplication.

## Test plan

- Docs/planning validation:
  `pdm run docs-validate`.
- Handoff validation if `.codex/handoff.md` changes:
  `pdm run handoff-validate`.
- `git diff --check`.
- No production behavior tests are expected in this planning-only slice.

## Rollback plan

Remove the planning PR slice and keep Document Converter inert until a new
reviewed planning package is created.
