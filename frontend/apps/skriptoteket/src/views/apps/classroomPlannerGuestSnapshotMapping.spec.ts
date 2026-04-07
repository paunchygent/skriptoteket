/**
 * Klassrumskartan guest snapshot mapping tests.
 *
 * These tests verify that the guest snapshot seam preserves the current app
 * structures we need later for authenticated import while deliberately
 * flattening transient undo/redo noise.
 */

import { describe, expect, it } from "vitest";

import {
  createClassroomPlannerGuestSnapshotFromSeed,
  hydrateGuestSnapshot,
} from "./classroomPlannerGuestSnapshotMapping";
import { resolveClassroomPlannerGuestStorageContract } from "./classroomPlannerGuestSnapshot";

describe("classroomPlannerGuestSnapshotMapping", () => {
  it("distinguishes the approved guest storage profiles", () => {
    expect(resolveClassroomPlannerGuestStorageContract("public_stateless")).toEqual({
      authority: "request",
      durable_browser_workspace: false,
      supports_authenticated_upgrade: false,
    });
    expect(resolveClassroomPlannerGuestStorageContract("public_browser_runtime")).toEqual({
      authority: "browser",
      durable_browser_workspace: true,
      supports_authenticated_upgrade: false,
    });
    expect(
      resolveClassroomPlannerGuestStorageContract("public_browser_workspace_with_upgrade"),
    ).toEqual({
      authority: "browser",
      durable_browser_workspace: true,
      supports_authenticated_upgrade: true,
    });
  });

  it("creates a versioned guest snapshot and hydrates it back into planner-friendly shapes", () => {
    const snapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-1",
      created_at: "2026-04-04T08:00:00.000Z",
      updated_at: "2026-04-04T08:00:00.000Z",
      expires_at: "2026-04-18T08:00:00.000Z",
      rosters: [
        {
          id: "roster-1",
          name: "SA24D",
          students: [
            { id: "student-1", display_name: "Alice Andersson" },
            { id: "student-2", display_name: "Bo Berg" },
          ],
        },
      ],
      templates: [
        {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 8,
          grid_rows: 6,
          seats: [{ id: "seat-1", x: 1, y: 1, zone: "front" }],
          fixtures: [],
        },
      ],
      smart_rule_sets: [
        {
          roster_id: "roster-1",
          revision: 3,
          seating_preferences: [{ student_id: "student-1", near_teacher: true }],
          relationship_rules: [{ id: "rule-1", kind: "keep_near", student_ids: ["student-1", "student-2"] }],
        },
      ],
      grouping_draft: {
        draft: {
          id: "draft-grouping-1",
          roster_id: "roster-1",
          draft_kind: "grouping",
          template_id: "template-1",
          smart_enabled: true,
          use_history: false,
          grouping_seating_distance_enabled: true,
          status: "active",
          revision: 7,
          last_opened_at: "2026-04-04T08:00:00.000Z",
        },
        roster: {
          id: "roster-1",
          name: "SA24D",
          students: [
            { id: "student-1", display_name: "Alice Andersson" },
            { id: "student-2", display_name: "Bo Berg" },
          ],
        },
        template: {
          id: "template-1",
          name: "Sal 101",
          grid_cols: 8,
          grid_rows: 6,
          seats: [{ id: "seat-1", x: 1, y: 1, zone: "front" }],
          fixtures: [],
        },
        groups: [{ id: "group-1", name: "Grupp 1", sort_order: 1, name_is_custom: false }],
        group_assignments: [{ student_id: "student-1", group_id: "group-1" }],
        seat_assignments: [],
        history_status: { can_undo: true, can_redo: true },
      },
      seating_draft: null,
      checkpoint_descriptors: [
        {
          local_id: "checkpoint-1",
          draft_kind: "grouping",
          created_at: "2026-04-04T08:05:00.000Z",
          label: "PDF-export",
          template_local_id: null,
          group_assignments: [{ student_id: "student-1", group_id: "group-1" }],
          seat_assignments: [],
        },
        {
          local_id: "checkpoint-2",
          draft_kind: "seating",
          created_at: "2026-04-04T08:06:00.000Z",
          label: "Poster-export",
          template_local_id: "template-1",
          group_assignments: [],
          seat_assignments: [{ student_id: "student-2", seat_id: "seat-1" }],
        },
      ],
      ui_state: {
        selected_roster_id: "roster-1",
        selected_template_id: "template-1",
        current_screen: "planner",
        planner_initial_view: "rules",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });

    const hydrated = hydrateGuestSnapshot(snapshot);

    expect(snapshot.schema_version).toBe(1);
    expect(snapshot.snapshot_content_hash).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(snapshot.rosters[0]?.fingerprint).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(snapshot.templates[0]?.fingerprint).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(snapshot.smart_rule_sets[0]?.fingerprint).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(snapshot.grouping_draft?.fingerprint).toMatch(/^sha256:[0-9a-f]{64}$/);
    expect(snapshot.grouping_draft?.task_entry_classroom_selection_mode).toBe("optional");
    expect(snapshot.checkpoint_descriptors[0]?.group_assignments).toEqual([
      { student_id: "student-1", group_id: "group-1" },
    ]);
    expect(snapshot.checkpoint_descriptors[1]?.template_local_id).toBe("template-1");
    expect(snapshot.checkpoint_descriptors[1]?.seat_assignments).toEqual([
      { student_id: "student-2", seat_id: "seat-1" },
    ]);

    expect(hydrated.rosters[0]?.id).toBe("roster-1");
    expect(hydrated.templates[0]?.id).toBe("template-1");
    expect(hydrated.grouping_draft?.draft.id).toBe("draft-grouping-1");
    expect(hydrated.grouping_draft?.history_status).toEqual({
      can_undo: false,
      can_redo: false,
    });
    expect(hydrated.ui_state.current_screen).toBe("planner");
    expect(hydrated.ui_state.planner_initial_view).toBe("rules");
    expect(hydrated.checkpoint_descriptors[0]?.source).toBe("export");
    expect(hydrated.checkpoint_descriptors[1]?.seat_assignments).toEqual([
      { student_id: "student-2", seat_id: "seat-1" },
    ]);
  });

  it("builds checkpoint fingerprints from export content instead of local labels", () => {
    const snapshot = createClassroomPlannerGuestSnapshotFromSeed({
      snapshot_id: "guest-snapshot-2",
      created_at: "2026-04-04T08:00:00.000Z",
      updated_at: "2026-04-04T08:00:00.000Z",
      expires_at: "2026-04-18T08:00:00.000Z",
      rosters: [],
      templates: [],
      smart_rule_sets: [],
      grouping_draft: null,
      seating_draft: null,
      checkpoint_descriptors: [
        {
          local_id: "checkpoint-a",
          draft_kind: "grouping",
          created_at: "2026-04-04T08:05:00.000Z",
          label: "Excel-export",
          template_local_id: null,
          group_assignments: [{ student_id: "student-1", group_id: "group-1" }],
          seat_assignments: [],
        },
        {
          local_id: "checkpoint-b",
          draft_kind: "grouping",
          created_at: "2026-04-04T08:06:00.000Z",
          label: "PDF-export",
          template_local_id: null,
          group_assignments: [{ student_id: "student-1", group_id: "group-1" }],
          seat_assignments: [],
        },
      ],
      ui_state: {
        selected_roster_id: null,
        selected_template_id: null,
        current_screen: "class-workspace",
        planner_initial_view: "groups",
        dismissed_grouping_draft_id: null,
        dismissed_seating_draft_id: null,
      },
    });

    expect(snapshot.checkpoint_descriptors[0]?.fingerprint).toBe(
      snapshot.checkpoint_descriptors[1]?.fingerprint,
    );
  });
});
