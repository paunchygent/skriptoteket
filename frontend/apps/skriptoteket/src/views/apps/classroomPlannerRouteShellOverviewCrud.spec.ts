/**
 * Planner overview CRUD flow tests.
 *
 * These tests keep the route-shell modal save handlers aligned with the live
 * planner state so edited classes and classrooms propagate without forcing the
 * teacher to leave the workspace.
 */

import { ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import { createClassroomPlannerOverviewCrudFlow } from "./classroomPlannerRouteShellOverviewCrud";
import type { ClassWorkspaceSummary, RoomTemplate, Roster } from "./classroomPlannerTypes";

function createSummary(): ClassWorkspaceSummary {
  return {
    roster: { id: "roster-1", name: "SA24D", student_count: 2 },
    task_entry_options: [
      { draft_kind: "grouping", classroom_selection_mode: "optional" },
      { draft_kind: "seating", classroom_selection_mode: "optional" },
    ],
    active_grouping_draft: null,
    active_seating_draft: {
      id: "draft-1",
      draft_kind: "seating",
      template_id: "template-1",
      template_name: "Sal 101",
      status: "active",
      revision: 3,
      last_opened_at: "2026-03-29T10:00:00Z",
      updated_at: "2026-03-29T10:00:00Z",
    },
    grouping_history: [],
    seating_history: [],
  };
}

describe("createClassroomPlannerOverviewCrudFlow", () => {
  it("pushes edited classrooms into the live planner template path", () => {
    const replaceActivePlannerTemplate = vi.fn();
    const flow = createClassroomPlannerOverviewCrudFlow(
      {
        availableRosters: ref<Roster[]>([]),
        availableTemplates: ref<RoomTemplate[]>([
          { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
        ]),
        selectedRosterId: ref<string | null>("roster-1"),
        selectedWorkspaceTemplateId: ref<string | null>("template-1"),
        currentScreen: ref<"class-workspace" | "planner">("planner"),
        classWorkspaceSummary: ref<ClassWorkspaceSummary | null>(createSummary()),
        plannerActionError: ref<string | null>(null),
      },
      {
        openClassWorkspace: vi.fn(),
        openInitialHomeWorkspace: vi.fn(),
        syncWorkspaceTemplateSelection: vi.fn(),
        replaceActivePlannerRoster: vi.fn(),
        replaceActivePlannerTemplate,
      },
    );

    flow.upsertTemplate({
      id: "template-1",
      name: "Sal 101 uppdaterad",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [],
    });

    expect(replaceActivePlannerTemplate).toHaveBeenCalledWith({
      id: "template-1",
      name: "Sal 101 uppdaterad",
      seats: [{ id: "seat-1", x: 0, y: 0, zone: null }],
      fixtures: [],
    });
  });

  it("pushes edited rosters into the live planner roster path", async () => {
    const replaceActivePlannerRoster = vi.fn();
    const flow = createClassroomPlannerOverviewCrudFlow(
      {
        availableRosters: ref<Roster[]>([{ id: "roster-1", name: "SA24D", students: [] }]),
        availableTemplates: ref<RoomTemplate[]>([]),
        selectedRosterId: ref<string | null>("roster-1"),
        selectedWorkspaceTemplateId: ref<string | null>(null),
        currentScreen: ref<"class-workspace" | "planner">("planner"),
        classWorkspaceSummary: ref<ClassWorkspaceSummary | null>(createSummary()),
        plannerActionError: ref<string | null>(null),
      },
      {
        openClassWorkspace: vi.fn(),
        openInitialHomeWorkspace: vi.fn(),
        syncWorkspaceTemplateSelection: vi.fn(),
        replaceActivePlannerRoster,
        replaceActivePlannerTemplate: vi.fn(),
      },
    );

    flow.activeRosterModal.value = { id: "roster-1", name: "SA24D", students: [] };
    await flow.upsertRoster({
      id: "roster-1",
      name: "SA24D uppdaterad",
      students: [{ id: "student-1", display_name: "Ada Lovelace" }],
    });

    expect(replaceActivePlannerRoster).toHaveBeenCalledWith({
      id: "roster-1",
      name: "SA24D uppdaterad",
      students: [{ id: "student-1", display_name: "Ada Lovelace" }],
    });
  });
});
