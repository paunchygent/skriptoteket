---
type: reference
id: REF-file-naming-save-export-protocol-v1
title: "File naming, save, and export protocol v1"
status: active
owners: "agents"
created: 2026-06-26
updated: 2026-06-27
topic: "file-naming-save-export"
---

# File Naming, Save, And Export Protocol V1

## Purpose

Teachers need downloaded files and `Mina filer` records that are easy to
recognize later. Generated names should carry source provenance, output
purpose, and enough version/time signal to distinguish repeated work without
making filenames noisy or technically brittle.

This reference is a planning baseline for a shared protocol. It should be
reviewed before production adoption.

## Scope

- Download filenames for curated-app exports.
- `Mina filer` save names for generated outputs.
- Editable save/download filename stems before export or save.
- Rename behavior for existing `Mina filer` records.
- Extension handling for generated, saved, and renamed files.
- App-owned outputs and producer-replay outputs.

## Ownership Model

File actions have two materially different authority shapes:

- **Application-owned output:** Skriptoteket owns the produced bytes or a stable
  local artifact. The app can compute the filename, content type, size, hash,
  and save metadata from local state.
- **Producer-replay output:** Sir Convert or another producer owns conversion
  and returned artifact authority. Skriptoteket owns teacher intent, source
  references, selected output purpose, visible naming, and `Mina filer` records,
  but it should not invent artifact truth that belongs to the producer.

Both shapes should flow through a shared file-action contract. App adapters may
vary only where authority differs. For both shapes, the protected backend/API
is the final filename authority for save and download actions. The browser may
collect or display a teacher-edited stem intent, but it must not own the final
filename, extension, or content-type truth.

## Naming Contract

Generated default names should have this logical shape:

```text
<source-title> - <output-purpose> - <version-or-timestamp>.<extension>
```

Rules:

- Use a source-derived title when a single source is clear.
- Use a canonical teacher-facing Swedish output-purpose label.
- Add a compact timestamp or version signal when repeated outputs are likely.
- Keep extensions owned by the system and derived from the selected output type.
- Do not duplicate extensions or file denominators, for example avoid
  `Audio Transcript Text.txt` and `text.txt.txt`.
- Preserve a stable source reference separately from the display name.
- Treat display names as editable labels, not as artifact authority.
- Normalize teacher-visible filenames as Unicode NFC, preserve Swedish
  characters where supported, and reject unsafe path/control/reserved-name
  variants rather than silently inventing browser-side replacements.
- Apply one shared backend-owned max-length policy before persistence or
  protected download response headers are emitted.

Canonical output-purpose labels:

| Use case | Canonical label | Notes |
|---|---|---|
| Transcript-style output | `Transkribering` | Use for transcript downloads/saves even when the chosen format is TXT, Markdown, VTT, or SRT. |
| Corrected exam output | `Rättat prov` | Use for reviewed/corrected teacher-facing exam outputs. |
| Converted PDF output | `Konverterad PDF` | Use when the output purpose is a PDF converted from another source. |
| Word-compatible document output | `Word-dokument` | Use when the output purpose is a DOCX/Word-compatible document converted from another source; the extension remains `.docx`. |
| Markdown output | `Markdown` | Use when Markdown is the teacher-recognizable output purpose. |
| Combined project output | `Sammanslagen PDF` | Use for one merged PDF from multiple/project inputs. |
| Separate project output | `Separat PDF` | Use for one file in a set of per-input/per-page outputs; add a system-owned distinguisher when several files share the same source title. |

The protocol prefers teacher-readable Swedish labels with spaces. ASCII-only
slug forms are not the default product surface and require an explicit adapter
or producer constraint.

## Editable Name Contract

Before download or `Spara i Mina filer`, the teacher should be able to edit the
filename stem where the workflow has enough context to offer a stable default.

The UI should:

- expose the editable stem and the protected extension separately;
- prevent empty names, path separators, control characters, and reserved names;
- show the resulting filename before the action completes;
- preserve the selected content type and extension unless the teacher chooses a
  different supported output format;
- use the same validation on download and save where possible;
- submit edited stem intent to the protected backend/API and consume the
  returned final sanitized filename for the completed save/download action.

## `Mina filer` Rename Contract

Saved files should be renameable after save.

Rename behavior should:

- update the `Mina filer` display filename, not mutate stored bytes;
- preserve extension/content-type consistency by default;
- reject names that would create unsafe paths or unsupported extension changes;
- keep existing source references, hashes, size, and created timestamp;
- reject same-owner display filename collisions with a named validation error;
- allow duplicate display names only if a future reviewed adapter explicitly
  accepts distinct duplicate records and proves the exception with tests.

Canonical default collision policy:

- Save/download generation may disambiguate repeated outputs with a
  system-owned timestamp or ordinal suffix.
- Manual rename does not auto-disambiguate collisions. It either succeeds with
  a unique final filename or fails with a named validation error such as
  `FILE_NAME_CONFLICT`.

## Duplicate Saves

Repeated saves of the same generated output should be explicit. The canonical
default for all apps is:

- create a new saved file record for the same owner;
- keep the same stable source reference where applicable;
- use a backend-generated final filename with a system-owned disambiguator when
  the default teacher-visible name would otherwise collide.

If a future app needs idempotent "update existing saved record" behavior, that
must be declared as an app-specific exception, reviewed, and tested as a
separate contract. Save/download parity must still use server-owned final
filename authority.

## Download Authority Contract

Protected download/save APIs must expose the final filename chosen by the
shared contract. Acceptable surfaces include response metadata and
`Content-Disposition`.

Rules:

- The backend/domain contract chooses the final sanitized filename for both
  download and save actions.
- The browser may preview a teacher-edited stem, but it must not reconstruct
  the final filename after the response returns.
- App-owned and producer-replay flows both prove parity by consuming the
  protected API filename result, not by duplicating filename assembly logic in
  frontend code.

## App Adapter Questions

Each app adoption slice must answer:

- What is the source title?
- What source reference is stable and safe to store?
- Which output-purpose labels are teacher-meaningful?
- Is the output app-owned or producer-replay-owned?
- Which fields are available before download/save: content type, extension,
  size, hash, producer artifact id, local artifact id?
- Can the teacher edit the name before both download and `Mina filer` save?
- Does the app need duplicate saved records or update-in-place behavior?
- Which canonical purpose labels from this reference apply to each output?
- How does the protected API return the final sanitized filename for download
  and save completion?

## Non-Goals

- No project/workspace restoration contract.
- No cross-app persistence model that forces all apps into one artifact shape.
- No browser-owned file authority for producer replay outputs.
- No automatic migration of existing saved file names.
