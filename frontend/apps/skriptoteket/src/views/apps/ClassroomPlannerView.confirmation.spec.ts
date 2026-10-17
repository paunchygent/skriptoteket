/** Root planner view: confirmation. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  stateMocks,
  routerMocks,
  flushPromises,
  resetPlannerViewState,
} from "./ClassroomPlannerView.test-support";
import ClassroomPlannerView from "./ClassroomPlannerView.vue";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

describe("ClassroomPlannerView: confirmation", () => {
  beforeEach(resetPlannerViewState);

  it("prompts before leaving when pending autosave does not finish promptly", async () => {
    window.history.replaceState({ classroomPlannerEntryOrigin: "dashboard" }, "");
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue({
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [],
    });
    stateMocks.plannerState.resolveDraft.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = { id: "template-1", name: "Sal 101", seats: [], fixtures: [] };
      stateMocks.plannerState.draft = {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "seating",
        template_id: "template-1",
        status: "active",
        revision: 3,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });
    stateMocks.plannerState.prepareForPlannerExit.mockResolvedValue({
      status: "confirm-discard",
    });
    vi.spyOn(window.performance, "getEntriesByType").mockReturnValue([]);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-seating' @click=\"$emit('open-seating', { templateId: 'template-1' })\">Öppna sittplatser</button>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='exit-app' @click=\"$emit('exit-app')\">Avsluta</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-seating']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='exit-app']").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Lämna Klassrumskartan?");
    expect(routerMocks.router.replace).not.toHaveBeenCalled();

    await wrapper.get("[data-test='confirm-dialog-confirm']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.discardPendingSessionWork).toHaveBeenCalled();
    expect(routerMocks.router.replace).toHaveBeenCalledWith({ name: "home" });

    wrapper.unmount();
  });

  it("confirms classroom deletion from overview without opening the edit modal", async () => {
    const summary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: null,
      active_seating_draft: {
        id: "draft-seating-1",
        draft_kind: "seating",
        template_id: "template-1",
        template_name: "Sal 101",
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-23T08:00:00Z",
        updated_at: "2026-03-23T08:00:00Z",
      },
      grouping_history: [],
      seating_history: [],
    };
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(summary);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    clientMocks.apiDelete.mockResolvedValue(undefined);
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          PlannerClassWorkspace: {
            template:
              "<div><button type='button' data-test='delete-current-template' @click=\"$emit('delete-current-template')\">Ta bort klassrum</button></div>",
          },
          PlannerWorkspaceShell: true,
          CreateRosterModal: true,
          CreateRoomTemplateModal: {
            template: "<div data-test='template-modal'>template-modal</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='delete-current-template']").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Är du säker?");
    expect(wrapper.text()).toContain(
      "tas bort från översikten tillsammans med alla beroende grupp- och sittutkast som använder klassrummet.",
    );
    expect(wrapper.find("[data-test='template-modal']").exists()).toBe(false);

    await wrapper.get("[data-test='confirm-dialog-confirm']").trigger("click");
    await flushPromises();

    expect(clientMocks.apiDelete).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/templates/template-1",
    );
    expect(wrapper.text()).not.toContain("Är du säker?");

    wrapper.unmount();
  });

  it("confirms roster deletion from overview without opening the roster modal", async () => {
    const summary: ClassWorkspaceSummary = {
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
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(summary);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    clientMocks.apiDelete.mockResolvedValue(undefined);
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          PlannerClassWorkspace: {
            template:
              "<div><button type='button' data-test='delete-current-roster' @click=\"$emit('delete-current-roster')\">Ta bort klasslista</button></div>",
          },
          PlannerWorkspaceShell: true,
          CreateRoomTemplateModal: true,
          CreateRosterModal: {
            template: "<div data-test='roster-modal'>roster-modal</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='delete-current-roster']").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Är du säker?");
    expect(wrapper.text()).toContain(
      "tas bort från översikten tillsammans med alla beroende grupp- och sittutkast för den klassen.",
    );
    expect(wrapper.find("[data-test='roster-modal']").exists()).toBe(false);

    await wrapper.get("[data-test='confirm-dialog-confirm']").trigger("click");
    await flushPromises();

    expect(clientMocks.apiDelete).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1",
    );
    expect(wrapper.text()).not.toContain("Är du säker?");

    wrapper.unmount();
  });

  it("shows roster delete failures inside the confirmation dialog", async () => {
    const summary: ClassWorkspaceSummary = {
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
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(summary);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    clientMocks.apiDelete.mockRejectedValueOnce(new Error("Kunde inte ta bort klasslistan just nu."));
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          PlannerClassWorkspace: {
            template:
              "<div><button type='button' data-test='delete-current-roster' @click=\"$emit('delete-current-roster')\">Ta bort klasslista</button></div>",
          },
          PlannerWorkspaceShell: true,
          CreateRoomTemplateModal: true,
          CreateRosterModal: true,
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='delete-current-roster']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='confirm-dialog-confirm']").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("Är du säker?");
    expect(wrapper.text()).toContain("Kunde inte ta bort klasslistan just nu.");

    wrapper.unmount();
  });
});
