# Klassrumskartan (Group Seating Studio)

Klassrumskartan is a teacher-specific planning application within the Skriptoteket ecosystem for classroom grouping and seat assignment. It uses the **class roster** as the primary anchor for all planning workflows.

## Domain Architecture

The application implements a Layered/DDD architecture to separate planning logic from persistence and web concerns.

### 1. Domain Layer (`src/skriptoteket/domain/curated_apps/classroom_planner/`)
- **Core Logic**: Smart-seating solver heuristics and heuristic class-list parsers.
- **Smart Rules**: Implementation of teacher-defined relationship clusters (Keep Near/Keep Apart for 2+ students) and teacher-distance preferences.
- **Invariants**: Enforcement of room geometry and roster consistency.

### 2. Application Layer (`src/skriptoteket/application/curated_apps/classroom_planner/`)
- **Orchestration**: Coordination between web controllers and domain services.
- **Draft Lifecycle**: Management of `PlanDraft` state transitions, autosave triggers, and snapshot finalization.
- **Export Translation**: Projection of internal seating models into poster-scene artifacts for PDF/XLSX generation.

### 3. Infrastructure Layer (`src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/`)
- **Persistence**: SQLAlchemy repositories for rosters, room templates, and drafts.
- **Adapters**: Document extractors for importing class lists from PDF/Text sources.
- **Registry**: Application entry point within the curated app registry.

## Core Abstractions

### PlanDraft & DraftKinds
Planning state is handled through `PlanDraft` objects to separate active work-in-progress from finalized records.
- **Seating Drafts**: Class-scoped drafts tied to a specific room template and lesson mode.
- **Grouping Drafts**: Class-scoped drafts for student clustering, optionally classroom-agnostic.

### Lesson Modes
Standardized workspace configurations that pre-define geometry constraints: `Standard`, `Test`, `Group Work`, and `Lab`.

### Dual-Map Authoring
The `Regler` (Rules) workspace provides a split interaction model:
- **Planning Map**: An alphabetical/ordered projection for student-based rule assignment.
- **Seating Map**: A spatial projection mirroring the physical classroom geometry.

## Technical Specification

- **Backend**: FastAPI / PostgreSQL / SQLAlchemy.
- **Frontend**: Vue 3 (Composition API) / Vite / Tailwind CSS.
- **State Management**: Component-local `ref/reactive` state for workspace interactions; backend-driven persistence for session continuity.
- **Exports**: Local browser-side rendering for PDF artifacts via CSS print-media queries and poster-scene translations.

## Status, Constraints, and Roadmap

### Current Limitations
- **Single Active Draft**: Each class supports exactly one active `SeatingDraft` and one `GroupingDraft`. Creating a new draft of the same kind automatically demotes the previous one to history.
- **In-Workspace History**: Undo/redo is limited to the current active draft session. There is no long-term "saved arrangements" archive beyond finalized export checkpoints.
- **Desktop-First**: The workspace is designed for full-viewport desktop use; mobile support is currently a port of the desktop workflow and lacks optimized touch-first interactions.

### Roadmap (ST-27 / ST-29)
- **Smart Grouping V1**: Extension of the smart-seating solver to support cluster-based student assignment (`ST-27-04`).
- **Explainable Suggestions**: UI feedback for solver decisions and alternate placement options (`ST-27-05`).
- **Dashboard Redesign**: Redesign of the `Översikt` hierarchy to a class-first dashboard model (`ST-29-04`).
- **Custom Tooltip System**: Implementation of a shared tooltip and global hover contract for dense workspace information (`ST-29-08`).

## Verification

- **Browser Smoke**: `scripts/playwright_classroom_planner_smoke.py` covers roster import, workspace transitions, and export flows.
- **UI Doctrine**: Documentation of design decisions available in `docs/reference/ref-klassrumskartan-workspace-ui-doctrine-2026-03-28.md`.
