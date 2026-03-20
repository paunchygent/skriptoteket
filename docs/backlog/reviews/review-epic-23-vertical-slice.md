---
type: review
id: REV-EPIC-23
title: "Classroom Planner Slice 1 Implementation Review"
status: changes_requested
owners: ["agents", "external-architect"]
created: 2026-03-20
epic: "EPIC-23"
reviewer: "@external-architect"
---

### TL;DR

Slice 1 is a credible vertical slice. The curated app is registered as `bespoke_required`, the backend exposes app-specific bootstrap and CRUD endpoints, DI wiring exists for repositories and services, the frontend uses a normalized Pinia store with separate group and seat assignment maps, and autosaved `PlanDraft` persistence is now present end-to-end. That is a real foundation, not a mock.

It is **not** accurate, however, to treat EPIC-23 as fully compliant with ADR-0069 or fully complete against the updated stories. The biggest gaps are: assignments are still persisted as JSONB blobs instead of separate assignment entities; draft reload/restore is not actually implemented on the frontend; `StudentPlanningMeta` / metadata drawer is missing; group lifecycle management is missing; server-side invariant and ownership validation is too weak; mutating endpoints are not protected with CSRF dependencies; and migration coverage does not include the latest draft migration or a full `upgrade head` no-op check.

## Assessment of Slice 1

### What is strong

The implementation gets the broad product framing right. It is a first-class curated app with bespoke routing and a dedicated `/api/v1/apps/classroom.group-seating-studio/*` surface, not a generic runner UI. The registry entry, bootstrap endpoint, roster/template CRUD, draft create/get/patch endpoints, request-scoped Dishka provider wiring, and happy-path service/API tests all point in the right architectural direction.

The frontend state model is materially better than the original prototype. `useClassroomState.ts` separates `groupAssignmentsByStudentId` from `seatAssignmentsByStudentId`, exposes explicit reducers, and computes derived views such as `ungroupedStudents`, `unseatedStudents`, `studentsByGroupId`, and `studentBySeatId`. The group and seat canvases dispatch actions rather than relying on cross-list destructive mutation. That aligns well with the “two projections of one normalized draft state” rule.

Using native HTML5 drag-and-drop instead of letting a library own canonical state is also a sound implementation choice here. It reduces hidden mutation paths and makes the reducer boundary clearer. That is stronger than a naïve `v-model` drag implementation.

### Where Slice 1 still fails the architecture

The largest ADR mismatch is persistence shape. ADR-0069 says `GroupAssignment` and `SeatAssignment` are scoped persistence concepts, but the actual implementation stores both as JSONB maps directly on `classroom_planner_plan_drafts`; there are no separate assignment tables or entities yet. That means the code does **not** fully implement the persistence model it claims to have accepted. Either the ADR must be narrowed, or the persistence model must be refactored before Slice 2 adds constraints, validation, and snapshots.

The frontend does not satisfy the “restore incomplete draft on reload” acceptance criterion. The store can `createDraft()` and debounced autosave via `_triggerAutosave()`, and the backend exposes `GET /drafts/{draft_id}`, but there is no `loadDraft()` / hydrate action, no persisted draft identifier across reload, and the view always returns to bootstrap + selection on a fresh load. In other words, autosave exists, but resume does not.

`StudentPlanningMeta` is still absent from the shipped Slice 1 code. The packaged frontend contains `ClassroomPlannerView.vue`, `GroupBoard.vue`, `GroupCard.vue`, `RoomCanvas.vue`, `SeatNode.vue`, and `useClassroomState.ts`, but there is no metadata drawer, no planning-meta domain model, and no teacher-only constraint editing surface. That means one of ST-23-02’s observable behaviors is still unimplemented.

Group lifecycle is also incomplete. The updated story says teachers should be able to add, remove, rename, and reorder group buckets, but the actual store only has `initializeGroups(count)` and the planner hardcodes `initializeGroups(6)` when planning starts. No group metadata is persisted in `PlanDraft`, so custom group structure cannot survive reload even if draft loading existed.

Server-side invariant enforcement is currently too weak. The API accepts `students`, `seats`, `group_assignments`, and `seat_assignments` largely as raw structured payloads, but there are no validators ensuring unique student IDs inside a roster, unique seat IDs inside a room template, valid lesson mode IDs, or that draft assignment payloads only reference students/seats/groups that exist in the chosen roster/template/draft context. The frontend reducers enforce some invariants locally, but the backend will happily store malformed state if called directly. That is a real boundary problem, not a cosmetic one.

Ownership checks are incomplete on draft creation. `get_roster()` and `get_template()` enforce owner matching, but `create_draft()` accepts `roster_id` and `template_id` and persists them without first verifying that those assets belong to the current user. The foreign keys guarantee existence, not authorization. Slice 2 should not build on that.

The autosave design is also missing concurrency protection. ST-23-06’s implementation notes mention optimistic revision/version fields, but the migration, SQLAlchemy model, DTOs, and PATCH endpoint contain no revision counter or `expected_revision` field. With multiple tabs or rapid save races, last-write-wins overwrite is currently silent.

There is also frontend contract drift. `ClassroomPlannerView.vue` and `useClassroomState.ts` use raw `fetch(...)` calls and even hardcoded fallback lesson modes if bootstrap is non-OK, instead of treating the backend bootstrap as the source of truth through the typed frontend API client. For a curated app whose backend owns policy and presets, silent hardcoded fallback is the wrong failure mode.

The web layer needs a security correction before more mutating endpoints are added. The POST/PUT/PATCH/DELETE routes in `apps_classroom_planner.py` depend on `require_user_api`, but there is no CSRF dependency on the mutating operations. That is not a Slice 2 feature; it is a correctness fix for the current Slice 1 API surface.

Migration coverage is incomplete. There are two classroom-planner migrations in the package, but the integration idempotency test targets only revision `57a6ea32ef0a` and verifies the roster/template tables, not the later `f30ac060991c` draft migration, and it does not perform the required “upgrade head twice is a no-op” check. That needs to be fixed before the migration surface grows again.

Finally, from an application-architecture perspective, the code is drifting toward a broad service object. `ClassroomPlannerService` now owns roster CRUD, template CRUD, and draft CRUD. That is still manageable in Slice 1, but Slice 2 should **not** continue expanding this class with suggestions, validation, and snapshot finalization. Your repo standards prefer one handler per use case and protocol-first seams at the web boundary.

## Architectural guidance for Slice 2

### 1. Suggestion Engine Location

**Approve:** **server-side Python**, not browser-only.

Put the actual rule evaluation and scoring engine in the **domain/application backend**, not in Pinia or TypeScript. The browser should remain a rich editor and renderer, but the authoritative suggestion engine should live in Python where it can access prior snapshots, constraints, lesson-mode presets, and future audit metadata in one place.

Use this layering:

* **Domain**: pure rule objects and evaluation/scoring functions.
* **Application**: handlers that load the draft, roster, template, constraint set, and relevant history; call the domain engine; return typed view models.
* **Web**: bespoke app endpoints only.
* **Frontend**: request suggestions, render alternatives, apply a chosen suggestion back into the draft.

Do **not** duplicate the full scoring logic in TypeScript. That will drift immediately. If you want instant UX feedback, keep only tiny local checks in the client and let the backend remain the source of truth.

Recommended endpoints:

* `POST /drafts/{draft_id}/suggestions`
* `POST /drafts/{draft_id}/validate`
* `POST /drafts/{draft_id}/finalize`

### 2. Constraint Model

**Approve:** a **draft-scoped typed constraint aggregate**, kept separate from student card view data.

Do not store planning factors on roster cards or mix them into roster identity. Model them as draft-scoped planning inputs so the same class can be planned differently for different lesson contexts.

Use three explicit categories:

* **StudentPlanningMeta**: per-student factors keyed by `student_id` within a draft.
  Examples: teacher_proximity, independent_focus_support, stability_preference, preferred_zone, avoid_zone.

* **PairConstraint**: pairwise relationships keyed by `(draft_id, student_id_a, student_id_b)`.
  Examples: keep_apart, prefer_together, temporary_conflict, stable_pair.

* **PlanningProfile / weights**: draft-level or request-level instruction for the engine.
  Examples: focus_first, balance_first, rotation_first, with explicit weights.

Persistence recommendation:

* If you want the cleanest long-term model, add dedicated app tables for draft-scoped student and pair constraints.
* If you need one pragmatic step first, you can store a validated `ConstraintSet` JSONB on `PlanDraft`, but only if the schema is explicit, versioned, and validated on every write. Do not accept anonymous free-form blobs.

No matter which storage shape you choose, keep these objects out of `StudentCardViewModel`.

### 3. Validation UX

**Approve:** **hybrid**.

Use **real-time local hints** only for cheap, deterministic, immediately visible issues:

* lesson mode missing
* seat occupied during manual drag
* impossible drop target
* local keep-apart violation if both students are already loaded in memory

Use an explicit **server-side Validate** action as the authoritative pass:

* computes hard violations and soft warnings
* includes history-aware findings
* includes score explanations
* is re-run automatically inside `finalize`

That gives the teacher fast guidance without pretending the client is the rule engine.

### 4. Snapshot Finalization

Finalization must be a **transactional backend use case**, not a frontend export.

Recommended flow for `FinalizeDraftHandler`:

1. Load `PlanDraft`, `Roster`, `RoomTemplate`, and the draft’s constraint set.
2. Run the authoritative validation pass.
3. Reject finalization if any hard violations remain.
4. Create an immutable `ArrangementSnapshot` containing:

   * deep-copied roster content
   * deep-copied room template content
   * deep-copied constraint set
   * lesson mode
   * group assignments
   * seat assignments
   * engine metadata if a suggestion was applied
   * link to source draft id
5. Commit atomically.
6. Return a snapshot summary DTO.

Do **not** let snapshots point at mutable roster/template records as their source of truth. ADR-0069 already made the correct decision there.

## Recommendations / requirements for EPIC-24

Before EPIC-24 starts, I would add one cleanup story or fold these into the first Slice 2 stories:

1. **Bring Slice 1 into doc/code alignment**

   * add draft restore/load
   * add revision-based optimistic concurrency
   * add CSRF enforcement on mutating endpoints
   * fix migration coverage to latest head and no-op upgrade
   * either refactor assignment persistence to match ADR-0069 or amend ADR-0069 to match what you actually intend

2. **Split the broad service**

   * `GetBootstrapHandler`
   * `CreateDraftHandler`
   * `PatchDraftHandler`
   * `GenerateSuggestionsHandler`
   * `ValidateDraftHandler`
   * `FinalizeDraftHandler`

3. **Add backend validators**

   * unique student IDs inside a roster
   * unique seat IDs inside a template
   * valid lesson mode IDs
   * assignment payload consistency with draft context
   * owner checks on draft creation

4. **Introduce draft constraint persistence**

   * student meta
   * pair constraints
   * planning profile / weights

5. **Define the suggestion response contract**

   * suggestion id
   * label/profile
   * score breakdown
   * hard/soft findings
   * explanation bullets
   * proposed assignment patch or full assignment state

6. **Implement snapshot aggregate + finalize endpoint**

   * immutable deep copy
   * snapshot list/read
   * optional “duplicate snapshot to draft” follow-up story

## Decision approvals

**Suggestion Engine Location:**
✅ **Approved** — server-side Python, with pure domain rules and application handlers. Frontend renders and edits; backend evaluates and explains.

**Constraint Model:**
✅ **Approved** — draft-scoped typed constraint aggregate, separated from student card view data. Prefer dedicated app tables; validated JSONB is acceptable only as an explicitly versioned interim model.

**Validation UX:**
✅ **Approved** — hybrid. Cheap client hints plus authoritative server-side validate/finalize.
