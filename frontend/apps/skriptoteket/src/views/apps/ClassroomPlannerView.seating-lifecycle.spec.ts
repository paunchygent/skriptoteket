/** Root planner view: seating lifecycle. */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  stateMocks,
  flushPromises,
  createDeferred,
  resetPlannerViewState,
} from "./ClassroomPlannerView.test-support";
import ClassroomPlannerView from "./ClassroomPlannerView.vue";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

describe("ClassroomPlannerView: seating lifecycle", () => {
  beforeEach(resetPlannerViewState);

  it("starts a fresh seating draft from the live seating workspace and refreshes the summary", async () => {
    const initialWorkspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: null,
      active_seating_draft: {
        id: "seating-active-1",
        draft_kind: "seating",
        template_id: "template-1",
        template_name: "Sal 101",
        status: "active",
        revision: 4,
        last_opened_at: "2026-03-21T09:00:00Z",
        updated_at: "2026-03-21T09:05:00Z",
      },
      grouping_history: [],
      seating_history: [],
    };

    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    stateMocks.plannerState.getClassWorkspaceSummary
      .mockResolvedValueOnce(initialWorkspaceSummary)
      .mockResolvedValueOnce(initialWorkspaceSummary)
      .mockResolvedValueOnce(initialWorkspaceSummary);
    stateMocks.plannerState.resolveDraft.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = { id: "template-1", name: "Sal 101", seats: [], fixtures: [] };
      stateMocks.plannerState.draft = {
        id: "draft-2",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: "template-1",
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-seating' @click=\"$emit('open-seating', { templateId: null })\">Öppna sittplatser</button>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='new-seating-draft' @click=\"$emit('new-seating-draft', { templateId: 'template-1' })\">Nytt sittschema</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-seating']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='new-seating-draft']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.startNewSeatingDraft).toHaveBeenCalledWith("roster-1", "template-1");
    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenLastCalledWith("roster-1");
  });

  it("refreshes the planner summary after deleting a historic seating draft from the live workspace", async () => {
    const initialWorkspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [
        {
          id: "seating-history-1",
          draft_kind: "seating",
          template_id: "template-1",
          template_name: "Sal 101",
          status: "superseded",
          revision: 2,
          last_opened_at: "2026-03-21T08:00:00Z",
          updated_at: "2026-03-21T08:10:00Z",
        },
      ],
    };

    const refreshedWorkspaceSummary: ClassWorkspaceSummary = {
      ...initialWorkspaceSummary,
      seating_history: [],
    };

    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    stateMocks.plannerState.getClassWorkspaceSummary
      .mockResolvedValueOnce(initialWorkspaceSummary)
      .mockResolvedValueOnce(initialWorkspaceSummary)
      .mockResolvedValueOnce(refreshedWorkspaceSummary);
    stateMocks.plannerState.resolveDraft.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = { id: "template-1", name: "Sal 101", seats: [], fixtures: [] };
      stateMocks.plannerState.draft = {
        id: "draft-2",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: "template-1",
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-seating' @click=\"$emit('open-seating', { templateId: null })\">Öppna sittplatser</button>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='delete-seating-history' @click=\"$emit('delete-seating-history-draft', 'seating-history-1')\">Ta bort sitthistorik</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-seating']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='delete-seating-history']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.deleteSeatingHistoryDraft).toHaveBeenCalledWith("seating-history-1");
    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenLastCalledWith("roster-1");
  });

  it("ignores repeated seating lifecycle actions while a seating transition is already in flight", async () => {
    const initialWorkspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [
        {
          id: "seating-history-1",
          draft_kind: "seating",
          template_id: "template-1",
          template_name: "Sal 101",
          status: "superseded",
          revision: 2,
          last_opened_at: "2026-03-21T08:00:00Z",
          updated_at: "2026-03-21T08:10:00Z",
        },
      ],
    };

    const deleteDeferred = createDeferred<void>();

    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(initialWorkspaceSummary);
    stateMocks.plannerState.resolveDraft.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = { id: "template-1", name: "Sal 101", seats: [], fixtures: [] };
      stateMocks.plannerState.draft = {
        id: "draft-2",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: "template-1",
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });
    stateMocks.plannerState.deleteSeatingHistoryDraft.mockReturnValue(deleteDeferred.promise);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-seating' @click=\"$emit('open-seating', { templateId: null })\">Öppna sittplatser</button>",
          },
          PlannerWorkspaceShell: {
            props: ["seatingLifecycleBusy", "seatingHistoryBusyDraftId"],
            template: `
              <div>
                <button type='button' data-test='delete-seating-history' @click="$emit('delete-seating-history-draft', 'seating-history-1')">Ta bort sitthistorik</button>
                <button type='button' data-test='open-seating-history' @click="$emit('open-seating-history-draft', 'seating-history-1')">Öppna sitthistorik</button>
                <span data-test='busy-flag'>{{ seatingLifecycleBusy ? 'busy' : 'idle' }}</span>
              </div>
            `,
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-seating']").trigger("click");
    await flushPromises();

    await wrapper.get("[data-test='delete-seating-history']").trigger("click");
    await nextTick();
    expect(wrapper.get("[data-test='busy-flag']").text()).toBe("busy");

    await wrapper.get("[data-test='open-seating-history']").trigger("click");
    expect(stateMocks.plannerState.deleteSeatingHistoryDraft).toHaveBeenCalledTimes(1);
    expect(stateMocks.plannerState.activateSeatingHistoryDraft).not.toHaveBeenCalled();

    deleteDeferred.resolve(undefined);
    await flushPromises();
    await vi.waitFor(() => {
      expect(wrapper.get("[data-test='busy-flag']").text()).toBe("idle");
    });
  });

  it("opens seating directly even before a classroom has been chosen", async () => {
    const workspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [],
    };

    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(workspaceSummary);
    stateMocks.plannerState.resolveDraft.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = null;
      stateMocks.plannerState.draft = {
        id: "draft-2",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: null,
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-seating' @click=\"$emit('open-seating', { templateId: null })\">Öppna sittplatser</button>",
          },
          PlannerWorkspaceShell: {
            template: "<div>PlannerWorkspaceShellStub</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-seating']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.resolveDraft).toHaveBeenCalledWith("roster-1", null, "seating");
    expect(wrapper.text()).toContain("PlannerWorkspaceShellStub");

    wrapper.unmount();
  });
});
