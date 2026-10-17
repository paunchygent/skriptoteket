/** Root planner view: workspace navigation. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import {
  clientMocks,
  stateMocks,
  routerMocks,
  flushPromises,
  resetPlannerViewState,
} from "./ClassroomPlannerView.test-support";
import ClassroomPlannerView from "./ClassroomPlannerView.vue";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

describe("ClassroomPlannerView: workspace navigation", () => {
  beforeEach(resetPlannerViewState);

  it("switches grouping class from the live toolbar selector", async () => {
    const rosterOneSummary: ClassWorkspaceSummary = {
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
    const rosterTwoSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-2", name: "SA24E", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: {
        id: "grouping-active-2",
        draft_kind: "grouping",
        template_id: null,
        template_name: null,
        status: "active",
        revision: 2,
        last_opened_at: "2026-03-21T11:00:00Z",
        updated_at: "2026-03-21T11:05:00Z",
      },
      active_seating_draft: null,
      grouping_history: [],
      seating_history: [],
    };

    clientMocks.apiGet
      .mockResolvedValueOnce([
        { id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] },
        { id: "roster-2", name: "SA24E", students: [{ id: "s2", display_name: "Alan" }] },
      ])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    stateMocks.plannerState.getClassWorkspaceSummary
      .mockResolvedValueOnce(rosterOneSummary)
      .mockResolvedValueOnce(rosterOneSummary)
      .mockResolvedValueOnce(rosterTwoSummary)
      .mockResolvedValueOnce(rosterTwoSummary);
    stateMocks.plannerState.resolveDraft.mockImplementation(async (rosterId: string) => {
      stateMocks.plannerState.roster = {
        id: rosterId,
        name: rosterId === "roster-2" ? "SA24E" : "SA24D",
        students: [],
      };
      stateMocks.plannerState.template = null;
      stateMocks.plannerState.draft = {
        id: rosterId === "roster-2" ? "draft-2" : "draft-1",
        roster_id: rosterId,
        draft_kind: "grouping",
        template_id: null,
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });
    stateMocks.plannerState.loadWorkspace.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-2", name: "SA24E", students: [] };
      stateMocks.plannerState.template = null;
      stateMocks.plannerState.draft = {
        id: "grouping-active-2",
        roster_id: "roster-2",
        draft_kind: "grouping",
        template_id: null,
        status: "active",
        revision: 2,
        last_opened_at: "2026-03-21T11:00:00Z",
      };
    });

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-grouping' @click=\"$emit('open-grouping', { templateId: null })\">Öppna grupper</button>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='change-grouping-roster' @click=\"$emit('change-grouping-roster', { rosterId: 'roster-2' })\">Byt klass</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-test="open-grouping"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="change-grouping-roster"]').trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.loadWorkspace).toHaveBeenCalledWith("grouping-active-2");
    expect(stateMocks.plannerState.resolveDraft).toHaveBeenCalledWith("roster-1", null, "grouping");

    wrapper.unmount();
  });

  it("returns from the planner to the class workspace without abandoning the draft", async () => {
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
    stateMocks.plannerState.getResumableDraft
      .mockResolvedValueOnce({
        draft: {
          id: "draft-1",
          roster_id: "roster-1",
          draft_kind: "seating",
          template_id: "template-1",
          status: "active",
          revision: 3,
          last_opened_at: "2026-03-21T10:00:00Z",
        },
        roster_name: "SA24D",
        template_name: "Sal 101",
      })
      .mockResolvedValueOnce(null);
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
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(workspaceSummary);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<div><div>PlannerClassWorkspaceStub</div><button type='button' data-test='open-seating' @click=\"$emit('open-seating', { templateId: 'template-1' })\">Öppna sittplatser</button></div>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='return-to-workspace' @click=\"$emit('select-workspace-mode', 'overview')\">Översikt</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-seating']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='return-to-workspace']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.prepareForWorkspaceSwitch).toHaveBeenCalled();
    expect(stateMocks.plannerState.abandonDraft).not.toHaveBeenCalled();
    expect(stateMocks.plannerState.clearWorkspace).toHaveBeenCalled();
    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenCalledWith("roster-1");
    expect(wrapper.text()).toContain("PlannerClassWorkspaceStub");

    wrapper.unmount();
  });

  it("updates grouping classroom context inside the active grouping workspace", async () => {
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce(null);
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
    stateMocks.plannerState.resolveDraft.mockImplementation(async (_rosterId, templateId, draftKind) => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = templateId
        ? { id: templateId, name: "Sal 101", seats: [], fixtures: [] }
        : null;
      stateMocks.plannerState.draft = {
        id: "draft-grouping-1",
        roster_id: "roster-1",
        draft_kind: draftKind,
        template_id: templateId,
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
              "<button type='button' data-test='open-grouping' @click=\"$emit('open-grouping', { templateId: null })\">Öppna grupper</button>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='change-grouping-template' @click=\"$emit('change-grouping-template', { templateId: 'template-1' })\">Välj klassrum</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-grouping']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='change-grouping-template']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.resolveDraft).toHaveBeenNthCalledWith(1, "roster-1", null, "grouping");
    expect(stateMocks.plannerState.resolveDraft).toHaveBeenNthCalledWith(2, "roster-1", "template-1", "grouping");

    wrapper.unmount();
  });

  it("exits the planner to the stored dashboard origin without discarding the active draft", async () => {
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

    expect(stateMocks.plannerState.prepareForPlannerExit).toHaveBeenCalled();
    expect(stateMocks.plannerState.abandonDraft).not.toHaveBeenCalled();
    expect(stateMocks.plannerState.clearWorkspace).toHaveBeenCalled();
    expect(routerMocks.router.replace).toHaveBeenCalledWith({ name: "home" });

    wrapper.unmount();
  });

  it("reopens the class workspace for another roster from the compact overview", async () => {
    const firstSummary: ClassWorkspaceSummary = {
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
    const secondSummary: ClassWorkspaceSummary = {
      ...firstSummary,
      roster: { id: "roster-2", name: "NA25A", student_count: 2 },
      active_seating_draft: null,
    };
    stateMocks.plannerState.getClassWorkspaceSummary
      .mockResolvedValueOnce(firstSummary)
      .mockResolvedValueOnce(secondSummary);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    clientMocks.apiGet
      .mockResolvedValueOnce([
        { id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] },
        { id: "roster-2", name: "NA25A", students: [{ id: "s2", display_name: "Bo" }] },
      ])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          PlannerClassWorkspace: {
            props: ["workspaceSummary"],
            template:
              "<div><div data-test='workspace-name'>{{ workspaceSummary.roster.name }}</div><button type='button' data-test='switch-roster' @click=\"$emit('select-roster', 'roster-2')\">Byt klass</button></div>",
          },
          PlannerWorkspaceShell: true,
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
        },
      },
    });
    await flushPromises();
    await flushPromises();

    expect(wrapper.get("[data-test='workspace-name']").text()).toBe("SA24D");

    await wrapper.get("[data-test='switch-roster']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenNthCalledWith(1, "roster-1");
    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenNthCalledWith(2, "roster-2");
    expect(wrapper.get("[data-test='workspace-name']").text()).toBe("NA25A");

    wrapper.unmount();
  });
});
