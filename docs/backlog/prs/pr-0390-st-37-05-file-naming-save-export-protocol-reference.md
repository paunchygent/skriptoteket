---
type: pr
id: PR-0390
title: "ST-37-05 file naming/save/export protocol reference"
status: ready
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
stories:
  - "ST-37-05"
tags:
  - docs
  - files
  - exports
  - mina-filer
acceptance_criteria:
  - "Given current file action drift, when this planning slice closes, then a reviewed reference defines generated filename shape, extension ownership, duplicate-save behavior, editable stems, and `Mina filer` rename semantics."
  - "Given app-owned and producer-replay outputs differ, when the reference is reviewed, then it describes both authority shapes without forcing one artifact model."
  - "Given app implementation slices follow, when this PR closes, then each later PR has a clear app-adapter question set and proof obligations."
---

# PR-0390: ST-37-05 File Naming/Save/Export Protocol Reference

## Problem

Curated app downloads and `Mina filer` saves are beginning to repeat the same
problems in separate places: redundant filenames, weak source provenance,
extension drift risk, and app-specific save/export UX for similar work.

## Goal

Review and finalize
[REF-file-naming-save-export-protocol-v1](../../reference/ref-file-naming-save-export-protocol-v1.md)
as the cross-app planning contract for generated file names, editable save
names, extension handling, duplicate saves, and `Mina filer` rename behavior.

## Non-goals

- No production backend or frontend implementation.
- No migration of existing saved files.
- No app-specific adoption beyond planning the sequence.

## Implementation Plan

1. Review current save/export surfaces for Audio Transcription, Exam Converter,
   Document Converter, and `Mina filer`.
2. Update the reference with the smallest shared naming contract that fits all
   current authority shapes.
3. Confirm app-owned versus producer-replay distinctions.
4. Close or revise the follow-up PR slices before implementation begins.

## Test Plan

- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Revert this planning package and leave app-specific save/export naming unchanged
until a better shared protocol is reviewed.
