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

## Scope

- Multi-file upload support (UI + runner contract)
- Input manifest for file metadata discovery
- Backward compatibility for single-file scripts
- Native PDF output helper (future)
- Personalized tool settings stored in user memory (future)
- Interactive text/dropdown inputs (future)

## Out of scope

- External data source fetchers (LMS, HR system integrations)
- Drag-and-drop file reordering in UI
- ZIP auto-extraction (users upload individual files)

## Stories

- [ST-12-01: Multi-file upload support](../stories/story-12-01-multi-file-upload.md)
- [ST-12-02: Native PDF output helper](../stories/story-12-02-native-pdf-output-helper.md) (ready)
- [ST-12-03: Personalized tool settings](../stories/story-12-03-personalized-tool-settings.md) (ready)
- [ST-12-04: Interactive text/dropdown inputs](../stories/story-12-04-interactive-text-dropdown-inputs.md) (ready)

## Risks

- Breaking existing scripts if backward compatibility not properly handled (mitigate: preserve `SKRIPTOTEKET_INPUT_PATH` for single-file uploads)
- Large file uploads may hit timeout/memory limits (mitigate: enforce per-file and total size caps)
- Complex multi-file UI may confuse users (mitigate: default to simple single-file, show multi-file only when needed)

## Dependencies

- ADR-0031 (Multi-file input contract)
- EPIC-11 (Full SPA migration; especially ST-11-13 cutover)
- PRD-script-hub-v0.2 (source requirements)
