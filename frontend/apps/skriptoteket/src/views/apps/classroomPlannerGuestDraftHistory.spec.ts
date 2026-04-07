/**
 * Classroom planner guest draft history tests.
 *
 * These tests verify that guest undo/redo stays local to each browser-owned
 * draft and survives metadata acknowledgements without reopening the
 * authenticated history boundary.
 */

import { describe, expect, it } from "vitest";

import { createClassroomPlannerGuestDraftHistory } from "./classroomPlannerGuestDraftHistory";
import type { DraftWorkspaceResponse } from "./classroomPlannerTypes";

function createWorkspace(input: {
  draftId: string;
  draftKind?: "grouping" | "seating";
  revision?: number;
  templateId?: string | null;
  groupAssignments?: DraftWorkspaceResponse["group_assignments"];
  seatAssignments?: DraftWorkspaceResponse["seat_assignments"];
}): DraftWorkspaceResponse {
  return {
    draft: {
      id: input.draftId,
      roster_id: "roster-1",
      draft_kind: input.draftKind ?? "grouping",
      template_id: input.templateId ?? "template-1",
      task_entry_classroom_selection_mode: "optional",
      smart_enabled: false,
      use_history: false,
      grouping_seating_distance_enabled: false,
      status: "active",
      revision: input.revision ?? 1,
      last_opened_at: "2026-04-07T10:00:00Z",
    },
    roster: {
      id: "roster-1",
      name: "SA24D",
      students: [
        { id: "ada", display_name: "Ada" },
        { id: "alan", display_name: "Alan" },
      ],
    },
    template: {
      id: input.templateId ?? "template-1",
      name: "Sal 101",
      seats: [
        { id: "seat-1", x: 0, y: 0, zone: null },
        { id: "seat-2", x: 1, y: 0, zone: null },
      ],
      fixtures: [],
    },
    groups: [{ id: "group-a", name: "Grupp 1", sort_order: 0, name_is_custom: false }],
    group_assignments: input.groupAssignments ?? [],
    seat_assignments: input.seatAssignments ?? [],
    history_status: {
      can_undo: false,
      can_redo: false,
    },
  };
}

describe("createClassroomPlannerGuestDraftHistory", () => {
  it("keeps undo and redo stacks local to each guest draft id", () => {
    const history = createClassroomPlannerGuestDraftHistory();
    const initialGroupingWorkspace = createWorkspace({ draftId: "grouping-draft-1" });
    const editedGroupingWorkspace = createWorkspace({
      draftId: "grouping-draft-1",
      groupAssignments: [{ student_id: "ada", group_id: "group-a" }],
    });
    const seatingWorkspace = createWorkspace({
      draftId: "seating-draft-1",
      draftKind: "seating",
      seatAssignments: [{ student_id: "alan", seat_id: "seat-1" }],
    });

    history.bindWorkspace(initialGroupingWorkspace);
    history.captureWorkspace(editedGroupingWorkspace);
    history.bindWorkspace(seatingWorkspace);

    expect(history.getHistoryStatus("grouping-draft-1")).toEqual({
      can_undo: true,
      can_redo: false,
    });
    expect(history.getHistoryStatus("seating-draft-1")).toEqual({
      can_undo: false,
      can_redo: false,
    });

    expect(history.undo("grouping-draft-1")?.group_assignments).toEqual([]);
    expect(history.getHistoryStatus("grouping-draft-1")).toEqual({
      can_undo: false,
      can_redo: true,
    });
    expect(history.redo("grouping-draft-1")?.group_assignments).toEqual([
      { student_id: "ada", group_id: "group-a" },
    ]);
  });

  it("preserves undo availability when the current draft metadata is acknowledged", () => {
    const history = createClassroomPlannerGuestDraftHistory();
    history.bindWorkspace(createWorkspace({ draftId: "grouping-draft-1", revision: 1 }));
    history.captureWorkspace(
      createWorkspace({
        draftId: "grouping-draft-1",
        revision: 1,
        groupAssignments: [{ student_id: "ada", group_id: "group-a" }],
      }),
    );

    history.replaceCurrentWorkspace(
      createWorkspace({
        draftId: "grouping-draft-1",
        revision: 9,
        groupAssignments: [{ student_id: "ada", group_id: "group-a" }],
      }),
    );

    expect(history.getHistoryStatus("grouping-draft-1")).toEqual({
      can_undo: true,
      can_redo: false,
    });
    expect(history.undo("grouping-draft-1")?.draft.revision).toBe(1);
  });
});
