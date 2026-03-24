import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { useClassroomPlannerOverviewStore } from "./classroomPlannerOverviewStore";

describe("useClassroomPlannerOverviewStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("prefers the requested home roster when it exists in the catalog", () => {
    const store = useClassroomPlannerOverviewStore();
    store.setCatalog(
      [
        { id: "roster-1", name: "SA24A", students: [] },
        { id: "roster-2", name: "SA24B", students: [] },
      ],
      [],
    );
    store.selectedRosterId = "roster-1";

    expect(store.resolveHomeRosterId("roster-2")).toBe("roster-2");
  });

  it("falls back to the selected roster or first roster when choosing the home overview", () => {
    const store = useClassroomPlannerOverviewStore();
    store.setCatalog(
      [
        { id: "roster-1", name: "SA24A", students: [] },
        { id: "roster-2", name: "SA24B", students: [] },
      ],
      [],
    );
    store.selectedRosterId = "roster-2";

    expect(store.resolveHomeRosterId(null)).toBe("roster-2");

    store.selectedRosterId = "missing";
    expect(store.resolveHomeRosterId(null)).toBe("roster-1");
  });

  it("syncs the selected template to the active seating draft unless the current selection should be preserved", () => {
    const store = useClassroomPlannerOverviewStore();
    store.setCatalog(
      [{ id: "roster-1", name: "SA24A", students: [] }],
      [
        { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
        { id: "template-2", name: "Sal 202", seats: [], fixtures: [] },
      ],
    );
    store.classWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24A", student_count: 1 },
      task_entry_options: [],
      active_grouping_draft: null,
      active_seating_draft: {
        id: "draft-1",
        draft_kind: "seating",
        template_id: "template-2",
        template_name: "Sal 202",
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-24T10:00:00Z",
        updated_at: "2026-03-24T10:00:00Z",
      },
      grouping_history: [],
      seating_history: [],
    };

    store.syncWorkspaceTemplateSelection();
    expect(store.selectedWorkspaceTemplateId).toBe("template-2");

    store.selectedWorkspaceTemplateId = "template-1";
    store.syncWorkspaceTemplateSelection({ preserveCurrent: true });
    expect(store.selectedWorkspaceTemplateId).toBe("template-1");
  });

  it("hides overview resumable cards after they are dismissed", () => {
    const store = useClassroomPlannerOverviewStore();
    store.classWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24A", student_count: 1 },
      task_entry_options: [],
      active_grouping_draft: {
        id: "grouping-1",
        draft_kind: "grouping",
        template_id: null,
        template_name: null,
        status: "active",
        revision: 2,
        last_opened_at: "2026-03-24T10:00:00Z",
        updated_at: "2026-03-24T10:00:00Z",
      },
      active_seating_draft: {
        id: "seating-1",
        draft_kind: "seating",
        template_id: "template-1",
        template_name: "Sal 101",
        status: "active",
        revision: 3,
        last_opened_at: "2026-03-24T10:00:00Z",
        updated_at: "2026-03-24T10:00:00Z",
      },
      grouping_history: [],
      seating_history: [],
    };

    expect(store.visibleOverviewGroupingDraft?.id).toBe("grouping-1");
    expect(store.visibleOverviewSeatingDraft?.id).toBe("seating-1");

    store.dismissOverviewGroupingDraft();
    store.dismissOverviewSeatingDraft();

    expect(store.visibleOverviewGroupingDraft).toBeNull();
    expect(store.visibleOverviewSeatingDraft).toBeNull();
  });
});
