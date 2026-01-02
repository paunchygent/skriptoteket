---
type: epic
id: EPIC-12
title: "Advanced input and output handling"
status: active
owners: "agents"
created: 2025-12-21
outcome: "Scripts can accept multiple input files, generate native PDFs, and access user-specific settings, enabling complex multi-file workflows without manual file merging."
dependencies: ["EPIC-11"]
---

> Status note: EPIC-12 was blocked until EPIC-11 (full SPA migration) was complete.
> EPIC-11 cutover (ST-11-13) is complete as of **2025-12-23**. ST-12-01 is delivered as a backend/runtime contract;
> all remaining EPIC-12 work should be implemented directly in the SPA (no SSR duplication).
>
> Backlog hygiene note (2026-01-01): ST-06-08 and ST-09-02 are closed as superseded by the SPA cutover; legacy
> HTMX/Jinja editor and CSP assumptions no longer apply. Track editor UX gaps under EPIC-14 and CSP work under EPIC-09
> with an SPA-first scope.

## Scope

- Multi-file upload support (UI + runner contract)
- Input manifest for file metadata discovery
- Native PDF output helper (future)
- Personalized tool settings stored in user memory (future)
- Interactive text/dropdown inputs (future)
- Session-scoped file persistence for multi-step tools (ADR-0039)

## Out of scope

- External data source fetchers (LMS, HR system integrations)
- Drag-and-drop file reordering in UI
- ZIP auto-extraction (users upload individual files)

## Stories

- [ST-12-01: Multi-file upload support](../stories/story-12-01-multi-file-upload.md) (done)
- [ST-12-02: Native PDF output helper](../stories/story-12-02-native-pdf-output-helper.md) (done)
- [ST-12-03: Personalized tool settings](../stories/story-12-03-personalized-tool-settings.md) (done)
- [ST-12-04: Interactive text/dropdown inputs](../stories/story-12-04-interactive-text-dropdown-inputs.md) (done)
- [ST-12-05: Session-scoped file persistence](../stories/story-12-05-session-file-persistence.md) (done)
- [ST-12-06: Session file cleanup policies](../stories/story-12-06-session-file-cleanup.md) (ready)
- [ST-12-07: Explicit session file reuse controls](../stories/story-12-07-explicit-session-file-reuse-controls.md) (done)

## Risks

- Breaking existing scripts if contract changes are not coordinated (mitigate: migrate scripts and rely on `SKRIPTOTEKET_INPUT_MANIFEST`)
- Large file uploads may hit timeout/memory limits (mitigate: enforce per-file and total size caps)
- Complex multi-file UI may confuse users (mitigate: default to simple single-file, show multi-file only when needed)

## Dependencies

- ADR-0031 (Multi-file input contract)
- ADR-0039 (Session-scoped file persistence)
- EPIC-11 (Full SPA migration; especially ST-11-13 cutover)
- PRD-script-hub-v0.2 (source requirements)
