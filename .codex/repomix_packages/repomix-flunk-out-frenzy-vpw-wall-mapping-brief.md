# Flunk-Out Frenzy VPW Wall Mapping Brief

## Purpose

This package is for an outside agent with no access to the repository or donor clone.

Your job is to map the remaining physical board pieces of Flunk-Out Frenzy to the VPW donor table and
return a clear, exhaustive, donor-faithful wall mapping.

This is not a vibe-porting exercise.
This is not a gameplay-tuning exercise.
This is not a broad architecture review.

The goal is to identify exactly which donor wall objects correspond to the current board carriers, which
ones are still missing, and which nearby donor objects must be explicitly excluded because they are
targets, triggers, gates, or unrelated mechanisms rather than wall geometry.

## Required fidelity rules

- Treat the VPW donor as the source of truth for wall geometry.
- Do not accept “close enough” geometry or undocumented remaps.
- Do not merge drop targets, gates, or trigger footprints into lane or wall carriers.
- If the current schema cannot honestly represent a donor wall object, call that out explicitly instead
  of flattening it silently.
- Distinguish clearly between:
  - already ported donor wall carriers
  - missing donor wall carriers
  - nearby donor objects that are not wall carriers for this board mapping task

## Current known context

- The live port already carries the main launcher corridor walls:
  - `Wall95`
  - `Wall34`
  - `Wall010`
  - `Wall011`
  - `Apron1`
  - `Apron2`
- The current likely missing wall candidates are:
  - `Wall018`
  - `Wall019`
  - `Wall024`
- The following are known non-candidates for wall grafting:
  - `sw57`
  - `sw35`
  - `sw36`
  They are donor drop targets, not launcher or lane wall carriers.

## What you must return

Return one concise, well-structured Markdown report with these sections.

### 1. Current board wall mapping

Provide a table with one row per current live board carrier that is relevant to wall/boundary geometry.

Required columns:
- `Current board carrier`
- `Current file/export/id`
- `Mapped donor object(s)`
- `Role on the board`
- `Status`
  Use one of:
  - `ported`
  - `partially ported`
  - `unmapped`

### 2. Remaining donor wall candidates

Provide a table for every donor wall object that should still be considered for grafting.

Required columns:
- `Donor object`
- `Why it belongs to the board path`
- `What it connects to in the current board`
- `Recommended representation in our board`
  Use one of:
  - `rail`
  - `solid polygon`
  - `lane-region boundary`
  - `do not graft`
- `Reason for that representation`

### 3. Explicit exclusions

Provide a table of nearby donor objects that might be confused for wall carriers but should be excluded.

Required columns:
- `Donor object`
- `Actual donor role`
- `Why it is not part of the wall graft`

### 4. Ordered next graft list

Give a short ordered list of the next donor wall grafts to implement.

For each item include:
- donor filename
- why it should be next
- what live carrier(s) it should attach to

## Scope boundaries

Focus on the physical board geometry, especially:
- outer boundary
- upper-right receiving path
- shooter corridor and handoff
- lower-right return / inlane / outlane throat
- lower-third wall separators that physically shape lane flow

Do not spend time redesigning gameplay logic, bumper layout, targets, or flipper tuning.

## Package contents

This package contains:
- the current live donor map/spec files
- relevant wall/trigger/gate raw donor JSON files
- the current donor reference docs and handoff
- the relevant compile/spec files needed to see how wall carriers are represented today

Your answer should be precise enough that another implementation agent could take your mapping and graft
the remaining donor walls without guessing.
