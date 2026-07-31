---
type: reference
id: REF-SKRIPT-PRD-curated-app-klassrumskartan
title: 'Curated App: Klassrumskartan'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: prd
summary: 'Curated App: Klassrumskartan'
---

## Product Outcome And Users

### 1. Goal
Provide teachers with a dedicated, intelligent, and interactive "Group Seating Studio" to generate, manually adjust, and persist student groups and seating arrangements. Built as a first-class curated app, this tool prioritizes lesson mode, avoids claiming "optimal" social outcomes, and offers explainable suggestions.

### 2. Product Rules
1. **Lesson mode comes first**: Everything from constraints to suggestions depends on the selected lesson context (e.g., "Quiet individual work" vs "Collaborative task").
2. **Visible cards are presentation-only**: Hidden planning factors (like needs proximity, keep apart) never appear as badges on the card surface to avoid stigmatizing labels.
3. **Suggest and explain**: The engine provides alternatives and trade-offs rather than a single authoritative "optimal" result.

### 3. Core User Flow
1. **Setup**: Select roster, room template, lesson mode, and planning emphasis.
2. **Constraint Input**: Input teacher-only planning factors (needs teacher proximity, independent-focus support, etc.).
3. **Generate Suggestions**: The app returns ~3 explainable suggestions (Focus-first, Balance-first, Rotation-first).
4. **Manual Editing**: Synchronized Group and Room views allowing drag-and-drop of students and whole groups.
5. **Validate**: Returns hard violations (blocks saving) and soft warnings (trade-offs).
6. **Finalize and Save**: Creates an *immutable final snapshot* for reuse, completely separate from autosaving drafts.

### 4. Delivery Slices
- **Slice 1**: Registry entry, SPA shell, roster/room CRUD, lesson mode selection, manual drag/drop planner (no generation).
- **Slice 2**: Suggestion engine, constraints, validation panel, snapshot finalization, and snapshot reuse.
- **Slice 3**: History-aware scoring, compare-to-previous, PDF/XLSX export, and full Playwright coverage.

### 5. Non-goals
- Tracking student attendance or grading.
- Automated external SDS discovery or personality profiling (only teacher-defined rules).
- Multi-class master scheduling.

## Capability Direction

The source material below remains authoritative for this section.

## Boundaries And Non-Goals

The source boundaries and recovery limits remain preserved below.

## Success Signals

The source material below remains authoritative for this section.

## Governed Follow-Up

The source material below remains authoritative for this section.
