---
type: reference
id: REF-file-naming-save-export-protocol-v1
title: "File naming, save, and export protocol v1"
status: active
owners: "agents"
created: 2026-06-26
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
vary only where authority differs.

## Naming Contract

Generated default names should have this logical shape:

```text
<source-title> - <output-purpose> - <version-or-timestamp>.<extension>
```

Rules:

- Use a source-derived title when a single source is clear.
- Use a teacher-facing output-purpose label such as `transcript`,
  `corrected-exam`, `converted-pdf`, or `markdown`.
- Add a compact timestamp or version signal when repeated outputs are likely.
- Keep extensions owned by the system and derived from the selected output type.
- Do not duplicate extensions or file denominators, for example avoid
  `Audio Transcript Text.txt` and `text.txt.txt`.
- Preserve a stable source reference separately from the display name.
- Treat display names as editable labels, not as artifact authority.

## Editable Name Contract

Before download or `Spara i Mina filer`, the teacher should be able to edit the
filename stem where the workflow has enough context to offer a stable default.

The UI should:

- expose the editable stem and the protected extension separately;
- prevent empty names, path separators, control characters, and reserved names;
- show the resulting filename before the action completes;
- preserve the selected content type and extension unless the teacher chooses a
  different supported output format;
- use the same validation on download and save where possible.

## `Mina filer` Rename Contract

Saved files should be renameable after save.

Rename behavior should:

- update the `Mina filer` display filename, not mutate stored bytes;
- preserve extension/content-type consistency by default;
- reject names that would create unsafe paths or unsupported extension changes;
- keep existing source references, hashes, size, and created timestamp;
- allow duplicate display names only if the product explicitly accepts that
  duplicate records are distinct saved files.

## Duplicate Saves

Repeated saves of the same generated output should be explicit. The current
Document Converter direction is:

- create another saved file record;
- keep the same stable source reference;
- use a generated name that can be distinguished by timestamp or later rename.

If a future app needs idempotent "update existing saved record" behavior, that
must be declared in its app adapter and tested as a separate contract.

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

## Non-Goals

- No project/workspace restoration contract.
- No cross-app persistence model that forces all apps into one artifact shape.
- No browser-owned file authority for producer replay outputs.
- No automatic migration of existing saved file names.
