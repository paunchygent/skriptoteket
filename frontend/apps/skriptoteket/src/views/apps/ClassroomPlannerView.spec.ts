/**
 * Root planner view tests.
 *
 * These tests verify the top-level Klassrumskartan screen orchestration, with
 * focus on the landing-screen resume CTA and the transition into the new
 * class-workspace state.
 */

import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ClassroomPlannerView from "./ClassroomPlannerView.vue";
import type { ClassWorkspaceSummary, PlanDraft, RoomTemplate, Roster } from "./classroomPlannerTypes";

type PlannerStateMock = {
  roster: Roster | null;
  template: RoomTemplate | null;
  draft: PlanDraft | null;
  abandonDraft: ReturnType<typeof vi.fn>;
  cancelPendingSave: ReturnType<typeof vi.fn>;
  clearWorkspace: ReturnType<typeof vi.fn>;
  flushPendingSave: ReturnType<typeof vi.fn>;
  getClassWorkspaceSummary: ReturnType<typeof vi.fn>;
  resolveDraft: ReturnType<typeof vi.fn>;
  startNewGroupingDraft: ReturnType<typeof vi.fn>;
  loadWorkspace: ReturnType<typeof vi.fn>;
  getResumableDraft: ReturnType<typeof vi.fn>;
};

const clientMocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    roster: null,
    template: null,
    draft: null,
    abandonDraft: vi.fn(),
    cancelPendingSave: vi.fn(),
    clearWorkspace: vi.fn(),
    flushPendingSave: vi.fn(),
    getClassWorkspaceSummary: vi.fn(),
    resolveDraft: vi.fn(),
    startNewGroupingDraft: vi.fn(),
    loadWorkspace: vi.fn(),
    getResumableDraft: vi.fn(),
  }))(),
}));

vi.mock("../../api/client", () => ({
  apiGet: clientMocks.apiGet,
}));

vi.mock("./useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

async function flushPromises(): Promise<void> {
  await Promise.resolve();
  await Promise.resolve();
  await nextTick();
}

describe("ClassroomPlannerView", () => {
  beforeEach(() => {
    clientMocks.apiGet.mockReset();
    stateMocks.plannerState.abandonDraft.mockReset();
    stateMocks.plannerState.cancelPendingSave.mockReset();
    stateMocks.plannerState.clearWorkspace.mockReset();
    stateMocks.plannerState.flushPendingSave.mockReset();
    stateMocks.plannerState.getClassWorkspaceSummary.mockReset();
    stateMocks.plannerState.loadWorkspace.mockReset();
    stateMocks.plannerState.resolveDraft.mockReset();
    stateMocks.plannerState.startNewGroupingDraft.mockReset();
    stateMocks.plannerState.getResumableDraft.mockReset();
    stateMocks.plannerState.roster = null;
    stateMocks.plannerState.template = null;
    stateMocks.plannerState.draft = null;
  });

  it("shows resume CTA on the landing page instead of auto-opening the planner", async () => {
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue({
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
    });

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: true,
          PlannerWorkspaceShell: true,
        },
      },
    });
    await flushPromises();
    await flushPromises();

    expect(wrapper.text()).toContain("Fortsätt senaste utkastet");
    expect(wrapper.text()).not.toContain("Aktiv planering");
    expect(stateMocks.plannerState.resolveDraft).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("opens the class workspace after class selection instead of launching the planner directly", async () => {
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
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerWorkspaceShell: true,
          PlannerClassWorkspace: {
            template: "<div>PlannerClassWorkspaceStub</div>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get('[role="button"]').trigger("click");
    await flushPromises();
    await flushPromises();

    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenCalledWith("roster-1");
    expect(wrapper.text()).toContain("PlannerClassWorkspaceStub");
    expect(stateMocks.plannerState.resolveDraft).not.toHaveBeenCalled();

    wrapper.unmount();
  });

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

    await wrapper.get('[role="button"]').trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='open-grouping']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.resolveDraft).toHaveBeenCalledWith("roster-1", null, "grouping");
    expect(wrapper.text()).toContain("PlannerWorkspaceShellStub");

    wrapper.unmount();
  });

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

    await wrapper.get('[role="button"]').trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='edit-roster']").trigger("click");
    await flushPromises();

    expect(wrapper.get("[data-test='roster-modal']").text()).toContain("SA24D");

    wrapper.unmount();
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

    await wrapper.get('[role="button"]').trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='open-seating']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.resolveDraft).toHaveBeenCalledWith("roster-1", null, "seating");
    expect(wrapper.text()).toContain("PlannerWorkspaceShellStub");

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
    stateMocks.plannerState.flushPendingSave.mockResolvedValue(undefined);
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(workspaceSummary);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: {
            template: "<div>PlannerClassWorkspaceStub</div>",
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

    const continueButton = wrapper.findAll("button").find((button) => button.text() === "Fortsätt");
    expect(continueButton).toBeDefined();
    if (!continueButton) {
      throw new Error("Expected the landing view to render a Fortsätt button.");
    }
    await continueButton.trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='return-to-workspace']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.flushPendingSave).toHaveBeenCalled();
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

    await wrapper.get('[role="button"]').trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='open-grouping']").trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='change-grouping-template']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.resolveDraft).toHaveBeenNthCalledWith(1, "roster-1", null, "grouping");
    expect(stateMocks.plannerState.resolveDraft).toHaveBeenNthCalledWith(2, "roster-1", "template-1", "grouping");

    wrapper.unmount();
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
              "<button type='button' data-test='new-grouping-draft' @click=\"$emit('new-grouping-draft', { templateId: 'template-1' })\">Nytt grupputkast</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    await wrapper.get('[role="button"]').trigger("click");
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

  it("exits the planner to the landing page without discarding the active draft", async () => {
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
    stateMocks.plannerState.flushPendingSave.mockResolvedValue(undefined);

    const wrapper = mount(ClassroomPlannerView, {
      global: {
        stubs: {
          CreateRosterModal: true,
          CreateRoomTemplateModal: true,
          PlannerClassWorkspace: true,
          PlannerWorkspaceShell: {
            template:
              "<button type='button' data-test='exit-to-landing' @click=\"$emit('exit-to-landing')\">Avsluta</button>",
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    const continueButton = wrapper.findAll("button").find((button) => button.text() === "Fortsätt");
    expect(continueButton).toBeDefined();
    if (!continueButton) {
      throw new Error("Expected the landing view to render a Fortsätt button.");
    }
    await continueButton.trigger("click");
    await flushPromises();
    await wrapper.get("[data-test='exit-to-landing']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.flushPendingSave).toHaveBeenCalled();
    expect(stateMocks.plannerState.abandonDraft).not.toHaveBeenCalled();
    expect(stateMocks.plannerState.clearWorkspace).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Fortsätt senaste utkastet");

    wrapper.unmount();
  });
});
