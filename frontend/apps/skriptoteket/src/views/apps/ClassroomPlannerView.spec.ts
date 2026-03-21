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
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

const clientMocks = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

const stateMocks = vi.hoisted(() => ({
  plannerState: {
    roster: null,
    template: null,
    draft: null,
    abandonDraft: vi.fn(),
    clearWorkspace: vi.fn(),
    getClassWorkspaceSummary: vi.fn(),
    resolveDraft: vi.fn(),
    loadWorkspace: vi.fn(),
    getResumableDraft: vi.fn(),
  },
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
    stateMocks.plannerState.clearWorkspace.mockReset();
    stateMocks.plannerState.getClassWorkspaceSummary.mockReset();
    stateMocks.plannerState.loadWorkspace.mockReset();
    stateMocks.plannerState.resolveDraft.mockReset();
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
        { draft_kind: "seating", classroom_selection_mode: "required" },
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
});
