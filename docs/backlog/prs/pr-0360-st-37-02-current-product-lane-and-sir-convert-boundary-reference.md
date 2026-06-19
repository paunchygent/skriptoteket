---
type: pr
id: PR-0360
title: "ST-37-02 current product lane and Sir Convert boundary reference"
status: done
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
stories:
  - "ST-37-02"
tags:
  - docs
  - product-direction
  - conversion
dependencies:
  - "PR-0358"
  - "PR-0359"
acceptance_criteria:
  - "Given product direction has shifted toward bespoke apps, when this slice closes, then durable docs define the current app-family lanes and crosslink them from the relevant epics/stories."
  - "Given Sir Convert-a-Lot remains the heavy conversion/runtime boundary, when the docs are updated, then they explicitly keep native transcript, exam editing, sharing, QTI, and file-action state inside Skriptoteket where no heavy conversion is needed."
  - "Given the old script/editor surface remains valuable, when docs are updated, then they preserve aligned script/editor/runner capabilities without presenting them as the sole front-door value proposition."
---

# PR-0360: ST-37-02 Current Product Lane And Sir Convert Boundary Reference

## Problem

Several docs still describe broad "tool" or "conversion hub" surfaces without
making the current app lanes and Sir Convert boundary obvious.

## Goal

Turn the current product direction into durable crosslinked docs.

## Non-goals

- No frontend route, copy, or registry implementation.
- No new Sir Convert or HuleEdu contract.
- No QTI editor or DOCX implementation.

## Implementation plan

1. Promote the current product-lane framing into the durable docs needed after
   `PR-0358`.
2. Crosslink `EPIC-21`, relevant Exam Converter stories, transcript stories,
   and shell/dashboard planning docs to the boundary reference.
3. Identify any old docs that use generic Conversion Hub language in a way that
   should be repaired by `ST-37-04`.
4. Update `.codex/handoff.md` only with a short current-state pointer.

## Implementation Summary

Completed on 2026-06-18. The durable boundary reference is
[REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md).
It defines the current teacher-facing lanes, separates Sir Convert-owned heavy
conversion/model/runtime responsibilities from Skriptoteket-owned native product
state, and preserves script/editor/runner capability without treating it as the
sole front-door product story.

This slice made no frontend route, registry, API, Sir Convert, HuleEdu, QTI, or
DOCX implementation changes. `EPIC-37` remains `proposed` and `REV-EPIC-37`
remains pending; this docs-only doctrine does not replace that review gate.

## Test plan

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Verification

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert the reference/crosslink updates if review decides the product-lane names
or Sir Convert boundary need a different decision package.
