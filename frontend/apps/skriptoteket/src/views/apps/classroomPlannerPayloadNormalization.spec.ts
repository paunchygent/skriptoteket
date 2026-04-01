import { describe, expect, it } from "vitest";

import {
  normalizeClassroomPlannerSummary,
  normalizeClassroomPlannerWorkspace,
} from "./classroomPlannerPayloadNormalization";
import type { ClassWorkspaceSummary, DraftWorkspaceResponse } from "./classroomPlannerTypes";

describe("classroomPlannerPayloadNormalization", () => {
  it("fills in missing summary collections", () => {
    const normalized = normalizeClassroomPlannerSummary({
      roster: { id: "roster-1", name: "SA24D", student_count: 31 },
      task_entry_options: undefined,
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: undefined,
      seating_history: undefined,
    } as unknown as ClassWorkspaceSummary);

    expect(normalized.task_entry_options).toEqual([]);
    expect(normalized.grouping_history).toEqual([]);
    expect(normalized.seating_history).toEqual([]);
  });

  it("fills in missing workspace collections", () => {
    const normalized = normalizeClassroomPlannerWorkspace({
      draft: {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: null,
        status: "active",
        revision: 0,
        last_opened_at: "2026-04-01T09:00:00Z",
      },
      roster: {
        id: "roster-1",
        name: "SA24D",
        students: undefined,
      },
      template: {
        id: "template-1",
        name: "Sal 101",
        seats: undefined,
        fixtures: undefined,
      },
      groups: undefined,
      group_assignments: undefined,
      seat_assignments: undefined,
      history_status: { can_undo: false, can_redo: false },
    } as unknown as DraftWorkspaceResponse);

    expect(normalized.roster.students).toEqual([]);
    expect(normalized.template).toEqual({
      id: "template-1",
      name: "Sal 101",
      seats: [],
      fixtures: [],
    });
    expect(normalized.groups).toEqual([]);
    expect(normalized.group_assignments).toEqual([]);
    expect(normalized.seat_assignments).toEqual([]);
  });

  it("defaults missing workspace history status to a safe empty state", () => {
    const normalized = normalizeClassroomPlannerWorkspace({
      draft: {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: null,
        status: "active",
        revision: 0,
        last_opened_at: "2026-04-01T09:00:00Z",
      },
      roster: {
        id: "roster-1",
        name: "SA24D",
        students: [],
      },
      template: null,
      groups: [],
      group_assignments: [],
      seat_assignments: [],
      history_status: undefined,
    } as unknown as DraftWorkspaceResponse);

    expect(normalized.history_status).toEqual({
      can_undo: false,
      can_redo: false,
    });
  });
});
