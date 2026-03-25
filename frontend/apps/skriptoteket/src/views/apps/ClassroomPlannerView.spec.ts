/**
 * Root planner view tests.
 *
 * These tests verify the top-level Klassrumskartan screen orchestration, with
 * focus on the overview-first home surface, live planner transitions, and the
 * cutover exit-to-origin behavior.
 */

import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ClassroomPlannerView from "./ClassroomPlannerView.vue";
import type { ClassWorkspaceSummary, PlanDraft, RoomTemplate, Roster } from "./classroomPlannerTypes";

type PlannerStateMock = {
  activateGroupingHistoryDraft: ReturnType<typeof vi.fn>;
  activateSeatingHistoryDraft: ReturnType<typeof vi.fn>;
  deleteGroupingHistoryDraft: ReturnType<typeof vi.fn>;
  deleteSeatingHistoryDraft: ReturnType<typeof vi.fn>;
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
  startNewSeatingDraft: ReturnType<typeof vi.fn>;
  loadWorkspace: ReturnType<typeof vi.fn>;
  getResumableDraft: ReturnType<typeof vi.fn>;
};

const clientMocks = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  apiGet: vi.fn(),
}));

const stateMocks = vi.hoisted(() => ({
  plannerState: ((): PlannerStateMock => ({
    roster: null,
    template: null,
    draft: null,
    activateGroupingHistoryDraft: vi.fn(),
    activateSeatingHistoryDraft: vi.fn(),
    deleteGroupingHistoryDraft: vi.fn(),
    deleteSeatingHistoryDraft: vi.fn(),
    abandonDraft: vi.fn(),
    cancelPendingSave: vi.fn(),
    clearWorkspace: vi.fn(),
    flushPendingSave: vi.fn(),
    getClassWorkspaceSummary: vi.fn(),
    resolveDraft: vi.fn(),
    startNewGroupingDraft: vi.fn(),
    startNewSeatingDraft: vi.fn(),
    loadWorkspace: vi.fn(),
    getResumableDraft: vi.fn(),
  }))(),
}));
const routerMocks = vi.hoisted(() => ({
  router: {
    replace: vi.fn(),
  },
}));

vi.mock("../../api/client", () => ({
  apiDelete: clientMocks.apiDelete,
  apiGet: clientMocks.apiGet,
}));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual<typeof import("vue-router")>("vue-router");
  return {
    ...actual,
    useRouter: () => routerMocks.router,
  };
});

vi.mock("./useClassroomState", () => ({
  useClassroomState: () => stateMocks.plannerState,
}));

async function flushPromises(): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt += 1) {
    await Promise.resolve();
    await nextTick();
  }
}

function createDeferred<T>(): { promise: Promise<T>; resolve: (value: T) => void } {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

describe("ClassroomPlannerView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.restoreAllMocks();
    clientMocks.apiDelete.mockReset();
    clientMocks.apiGet.mockReset();
    routerMocks.router.replace.mockReset();
    stateMocks.plannerState.abandonDraft.mockReset();
    stateMocks.plannerState.activateGroupingHistoryDraft.mockReset();
    stateMocks.plannerState.activateSeatingHistoryDraft.mockReset();
    stateMocks.plannerState.cancelPendingSave.mockReset();
    stateMocks.plannerState.clearWorkspace.mockReset();
    stateMocks.plannerState.deleteGroupingHistoryDraft.mockReset();
    stateMocks.plannerState.deleteSeatingHistoryDraft.mockReset();
    stateMocks.plannerState.flushPendingSave.mockReset();
    stateMocks.plannerState.getClassWorkspaceSummary.mockReset();
    stateMocks.plannerState.loadWorkspace.mockReset();
    stateMocks.plannerState.resolveDraft.mockReset();
    stateMocks.plannerState.startNewGroupingDraft.mockReset();
    stateMocks.plannerState.startNewSeatingDraft.mockReset();
    stateMocks.plannerState.getResumableDraft.mockReset();
    stateMocks.plannerState.roster = null;
    stateMocks.plannerState.template = null;
    stateMocks.plannerState.draft = null;
    stateMocks.plannerState.flushPendingSave.mockResolvedValue(true);
    localStorage.clear();
    vi.spyOn(window.performance, "getEntriesByType").mockReturnValue([]);
    window.history.replaceState(null, "");
  });

  it("opens straight into the overview-first workspace using the resumable draft roster", async () => {
    const workspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
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
        last_opened_at: "2026-03-21T10:00:00Z",
        updated_at: "2026-03-21T10:00:00Z",
      },
      grouping_history: [],
      seating_history: [],
    };
    clientMocks.apiGet
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(workspaceSummary);
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

    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenCalledWith("roster-1");
    expect(wrapper.text()).not.toContain("Laddar planeringsmiljön");
    expect(stateMocks.plannerState.resolveDraft).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("prefers the persisted workspace selection over an older resumable draft on reload", async () => {
    localStorage.setItem("skriptoteket:classroom-planner:selected-roster-id", "roster-2");
    localStorage.setItem("skriptoteket:classroom-planner:selected-template-id", "template-2");

    const workspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-2", name: "SA24E", student_count: 1 },
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
      .mockResolvedValueOnce([
        { id: "roster-1", name: "SA24D", students: [] },
        { id: "roster-2", name: "SA24E", students: [] },
      ])
      .mockResolvedValueOnce([
        { id: "template-1", name: "Sal 101", seats: [], fixtures: [] },
        { id: "template-2", name: "Sal 202", seats: [], fixtures: [] },
      ]);
    stateMocks.plannerState.getClassWorkspaceSummary.mockResolvedValue(workspaceSummary);
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

    expect(stateMocks.plannerState.getClassWorkspaceSummary).toHaveBeenCalledWith("roster-2");

    wrapper.unmount();
  });

  it("opens the overview-first workspace immediately instead of waiting for a landing selection", async () => {
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
              "<button type='button' data-test='edit-grouping-roster' @click=\"$emit('edit-roster')\">Redigera klass</button>",
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
    stateMocks.plannerState.flushPendingSave.mockResolvedValue(true);
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
    stateMocks.plannerState.flushPendingSave.mockResolvedValue(true);

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

    expect(stateMocks.plannerState.flushPendingSave).toHaveBeenCalled();
    expect(stateMocks.plannerState.abandonDraft).not.toHaveBeenCalled();
    expect(stateMocks.plannerState.clearWorkspace).toHaveBeenCalled();
    expect(routerMocks.router.replace).toHaveBeenCalledWith({ name: "home" });

    wrapper.unmount();
  });

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
    const flushPendingSaveDeferred = createDeferred<boolean>();
    stateMocks.plannerState.flushPendingSave.mockReturnValue(flushPendingSaveDeferred.promise);
    vi.spyOn(window.performance, "getEntriesByType").mockReturnValue([]);
    vi.useFakeTimers();

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
    await vi.advanceTimersByTimeAsync(1600);
    await flushPromises();

    expect(wrapper.text()).toContain("Lämna Klassrumskartan?");
    expect(routerMocks.router.replace).not.toHaveBeenCalled();

    await wrapper.get("[data-test='confirm-dialog-confirm']").trigger("click");
    await flushPromises();

    expect(stateMocks.plannerState.cancelPendingSave).toHaveBeenCalled();
    expect(routerMocks.router.replace).toHaveBeenCalledWith({ name: "home" });
    vi.useRealTimers();

    wrapper.unmount();
  });

  it("passes overview resumable draft cards to the class workspace and dismisses them locally", async () => {
    const workspaceSummary: ClassWorkspaceSummary = {
      roster: { id: "roster-1", name: "SA24D", student_count: 1 },
      task_entry_options: [
        { draft_kind: "grouping", classroom_selection_mode: "optional" },
        { draft_kind: "seating", classroom_selection_mode: "optional" },
      ],
      active_grouping_draft: {
        id: "draft-grouping-1",
        draft_kind: "grouping",
        template_id: null,
        template_name: null,
        status: "active",
        revision: 2,
        last_opened_at: "2026-03-23T08:00:00Z",
        updated_at: "2026-03-23T08:10:00Z",
      },
      active_seating_draft: {
        id: "draft-seating-1",
        draft_kind: "seating",
        template_id: "template-1",
        template_name: "Sal 101",
        status: "active",
        revision: 5,
        last_opened_at: "2026-03-23T09:00:00Z",
        updated_at: "2026-03-23T09:10:00Z",
      },
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
            props: [
              "visibleGroupingDraft",
              "visibleSeatingDraft",
            ],
            template: `
              <div>
                <span data-test="grouping-card-prop">{{ visibleGroupingDraft?.id ?? "none" }}</span>
                <span data-test="seating-card-prop">{{ visibleSeatingDraft?.id ?? "none" }}</span>
                <button type="button" data-test="dismiss-grouping-card" @click="$emit('dismiss-grouping-draft')">dismiss grouping</button>
                <button type="button" data-test="dismiss-seating-card" @click="$emit('dismiss-seating-draft')">dismiss seating</button>
              </div>
            `,
          },
        },
      },
    });
    await flushPromises();
    await flushPromises();

    expect(wrapper.get('[data-test="grouping-card-prop"]').text()).toBe("draft-grouping-1");
    expect(wrapper.get('[data-test="seating-card-prop"]').text()).toBe("draft-seating-1");

    await wrapper.get('[data-test="dismiss-grouping-card"]').trigger("click");
    await wrapper.get('[data-test="dismiss-seating-card"]').trigger("click");
    await flushPromises();

    expect(wrapper.get('[data-test="grouping-card-prop"]').text()).toBe("none");
    expect(wrapper.get('[data-test="seating-card-prop"]').text()).toBe("none");
    expect(stateMocks.plannerState.abandonDraft).not.toHaveBeenCalled();

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
              "<div><button type='button' data-test='select-template' @click=\"$emit('select-template', 'template-1')\">Välj klassrum</button><button type='button' data-test='edit-current-template' @click=\"$emit('edit-current-template')\">Redigera klassrum</button></div>",
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
    expect(wrapper.find("[data-test='roster-modal']").exists()).toBe(false);

    await wrapper.get("[data-test='confirm-dialog-confirm']").trigger("click");
    await flushPromises();

    expect(clientMocks.apiDelete).toHaveBeenCalledWith(
      "/api/v1/apps/classroom.group-seating-studio/rosters/roster-1",
    );
    expect(wrapper.text()).not.toContain("Är du säker?");

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
