/** Root planner view: roster template editing. */

import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";

import {
  clientMocks,
  stateMocks,
  flushPromises,
  resetPlannerViewState,
} from "./ClassroomPlannerView.test-support";
import ClassroomPlannerView from "./ClassroomPlannerView.vue";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

describe("ClassroomPlannerView: roster template editing", () => {
  beforeEach(resetPlannerViewState);

  it("opens roster editing from the class workspace overview", async () => {
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

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='edit-roster' @click=\"$emit('edit-roster')\">Redigera roster</button>",
          },
          PlannerWorkspaceShell: true,
          CreateRoomTemplateModal: true,
          CreateRosterModal: {
            props: ["roster"],
            template: "<div data-test='roster-modal'>{{ roster?.name }}</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='edit-roster']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='roster-modal']").text()).toContain("SA24D");

    wrapper.unmount();
  });

  it("opens roster editing from the live grouping workspace settings path", async () => {
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
        draft_kind: "grouping",
        template_id: null,
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: {
            props: ["roster"],
            template: "<div data-test='roster-modal'>{{ roster?.name }}</div>",
          },
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-grouping' @click=\"$emit('open-grouping', { templateId: null })\">Öppna grupper</button>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='edit-grouping-roster' @click=\"$emit('edit-roster')\">Redigera</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get('[data-test="open-grouping"]').trigger("click");
    await flushPromises();
    await wrapper.get('[data-test="edit-grouping-roster"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-test="roster-modal"]').text()).toContain("SA24D");

    wrapper.unmount();
  });

  it("edits the seating draft template from overview resume actions even when another template is selected", async () => {
    const workspaceSummary: ClassWorkspaceSummary = {
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
        revision: 3,
        last_opened_at: "2026-03-23T09:00:00Z",
        updated_at: "2026-03-23T09:10:00Z",
      },
      grouping_history: [],
      seating_history: [],
    };

    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([
        { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
        { id: "template-2", name: "Sal 202", seats: [], fixtures: [] },
      ]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(workspaceSummary);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          PlannerWorkspaceShell: true,
          PlannerClassWorkspace: {
            template: `
              <div>
                <button type="button" data-test="select-template" @click="$emit('select-template', 'template-2')">Välj annat klassrum</button>
                <button
                  type="button"
                  data-test="edit-resume-template"
                  @click="$emit('edit-current-template', { id: 'template-1', name: 'Sal 101', seats: [], fixtures: [] })"
                >
                  Redigera resumeklassrum
                </button>
              </div>
            `,
          },
          CreateRoomTemplateModal: {
            props: ["template"],
            template: "<div data-test='template-modal'>{{ template?.name }}</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='select-template']").trigger("click");
    await wrapper.get("[data-test='edit-resume-template']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='template-modal']").text()).toContain("Sal 101");

    wrapper.unmount();
  });

  it("opens classroom editing from overview using the selected classroom", async () => {
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
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          PlannerClassWorkspace: {
            template:
              "<div><button type='button' data-test='select-template' @click=\"$emit('select-template', 'template-1')\">Välj klassrum</button><button type='button' data-test='edit-current-template' @click=\"$emit('edit-current-template')\">Redigera</button></div>",
          },
          PlannerWorkspaceShell: true,
          CreateRosterModal: true,
          CreateRoomTemplateModal: {
            props: ["template"],
            template: "<div data-test='template-modal'>{{ template?.name }}</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='select-template']").trigger("click");
    await wrapper.get("[data-test='edit-current-template']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='template-modal']").text()).toContain("Sal 101");

    wrapper.unmount();
  });

  it("opens the newly created class workspace directly from overview creation", async () => {
    const originalSummary: ClassWorkspaceSummary = {
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
    const newSummary: ClassWorkspaceSummary = {
      ...originalSummary,
      roster: { id: "roster-2", name: "NA25A", student_count: 2 },
    };
    stateMocks.plannerState.getClassWorkspaceSummary
      .mockResolvedValueOnce(originalSummary)
      .mockResolvedValueOnce(newSummary);
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
              "<div><div data-test='workspace-name'>{{ workspaceSummary.roster.name }}</div><button type='button' data-test='create-roster' @click=\"$emit('create-roster')\">Ny klasslista</button></div>",
          },
          PlannerWorkspaceShell: true,
          CreateRoomTemplateModal: true,
          CreateRosterModal: {
            template:
              "<button type='button' data-test='save-new-roster' @click=\"$emit('saved', { id: 'roster-2', name: 'NA25A', students: [{ id: 's2', display_name: 'Bo' }, { id: 's3', display_name: 'Cleo' }] })\">Spara klass</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    expect(wrapper.get("[data-test='workspace-name']").text()).toBe("SA24D");

    await wrapper.get("[data-test='create-roster']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='save-new-roster']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenNthCalledWith(1, "roster-1");
    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenNthCalledWith(2, "roster-2");
    expect(wrapper.get("[data-test='workspace-name']").text()).toBe("NA25A");

    wrapper.unmount();
  });
});
