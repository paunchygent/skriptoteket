/** Root planner view: grouping lifecycle. */

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

describe("ClassroomPlannerView: grouping lifecycle", () => {
  beforeEach(resetPlannerViewState);

  it("starts grouping without a classroom from the class workspace", async () => {
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
        id: "draft-1",
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
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-grouping' @click=\"$emit('open-grouping', { templateId: null })\">Öppna grupper</button>",
          },
          PlannerWorkspaceShell: {
            template: "<div>PlannerWorkspaceShellStub</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();
    await wrapper.get("[data-test='open-grouping']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.resolveDraft).toHaveBeenCalledWith("roster-1", null, "grouping");
    expect(wrapper.text()).toContain("PlannerWorkspaceShellStub");

    wrapper.unmount();
  });

  it("opens a historical grouping draft from the live grouping workspace", async () => {
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
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({
        draft: {
          id: "draft-history-1",
          roster_id: "roster-1",
          draft_kind: "grouping",
          template_id: null,
          status: "active",
          revision: 2,
          last_opened_at: "2026-03-21T11:00:00Z",
        },
        roster_name: "SA24D",
        template_name: null,
      });
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(workspaceSummary);
    stateMocks.plannerState.resolveDraft.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = null;
      stateMocks.plannerState.draft = {
        id: "draft-1",
        roster_id: "roster-1",
        draft_kind: "grouping",
        template_id: null,
        status: "active",
        revision: 1,
        last_opened_at: "2026-03-21T10:00:00Z",
      };
    });
    stateMocks.plannerState.activateGroupingHistoryDraft.mockImplementation(async () => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = null;
      stateMocks.plannerState.draft = {
        id: "draft-history-1",
        roster_id: "roster-1",
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
              "<button type='button' data-test='open-grouping-history' @click=\"$emit('open-grouping-history-draft', 'draft-history-1')\">Öppna historik</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-grouping']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='open-grouping-history']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.activateGroupingHistoryDraft).toHaveBeenCalledWith(
      "draft-history-1",
    );
  });

  it("refreshes the planner summary after deleting a historic grouping draft from the live workspace", async () => {
    const initialWorkspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: null,
      active_seating_draft: null,
      grouping_history: [
        {
          id: "draft-history-1",
          draft_kind: "grouping",
          template_id: null,
          template_name: null,
          status: "superseded",
          revision: 1,
          last_opened_at: "2026-03-21T09:00:00Z",
          updated_at: "2026-03-21T09:05:00Z",
        },
      ],
      seating_history: [],
    };

    const refreshedWorkspaceSummary: ClassWorkspaceSummary = {
      ...initialWorkspaceSummary,
      grouping_history: [],
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
      stateMocks.plannerState.template = null;
      stateMocks.plannerState.draft = {
        id: "draft-1",
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
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template:
              "<button type='button' data-test='open-grouping' @click=\"$emit('open-grouping', { templateId: null })\">Öppna grupper</button>",
          },
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='delete-grouping-history' @click=\"$emit('delete-grouping-history-draft', 'draft-history-1')\">Ta bort historik</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-grouping']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='delete-grouping-history']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.deleteGroupingHistoryDraft).toHaveBeenCalledWith(
      "draft-history-1",
    );
    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenCalledTimes(3);
    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenLastCalledWith("roster-1");
  });

  it("starts a blank grouping draft from the active grouping workspace", async () => {
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [{ id: "s1", display_name: "Ada" }] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({
        draft: {
          id: "draft-grouping-2",
          roster_id: "roster-1",
          draft_kind: "grouping",
          template_id: "template-1",
          status: "active",
          revision: 0,
          last_opened_at: "2026-03-21T12:00:00Z",
        },
        roster_name: "SA24D",
        template_name: "Sal 101",
      });
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
    stateMocks.plannerState.startNewGroupingDraft.mockImplementation(async (_rosterId, templateId) => {
      stateMocks.plannerState.roster = { id: "roster-1", name: "SA24D", students: [] };
      stateMocks.plannerState.template = templateId
        ? { id: templateId, name: "Sal 101", seats: [], fixtures: [] }
        : null;
      stateMocks.plannerState.draft = {
        id: "draft-grouping-2",
        roster_id: "roster-1",
        draft_kind: "grouping",
        template_id: templateId,
        status: "active",
        revision: 0,
        last_opened_at: "2026-03-21T12:00:00Z",
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
              "<button type='button' data-test='new-grouping-draft' @click=\"$emit('new-grouping-draft', { templateId: 'template-1' })\">Nytt utkast</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get("[data-test='open-grouping']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='new-grouping-draft']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.startNewGroupingDraft).toHaveBeenCalledWith(
      "roster-1",
      "template-1",
    );

    wrapper.unmount();
  });
});
