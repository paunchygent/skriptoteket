import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ClassroomPlannerView from "./ClassroomPlannerView.vue";

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
    resolveDraft: vi.fn(),
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
    stateMocks.plannerState.resolveDraft.mockReset();
    stateMocks.plannerState.getResumableDraft.mockReset();
    stateMocks.plannerState.roster = null;
    stateMocks.plannerState.template = null;
    stateMocks.plannerState.draft = null;
  });

  it("shows resume CTA on the landing page instead of auto-opening the planner", async () => {
    clientMocks.apiGet
      .mockResolvedValueOnce({ lesson_modes: [], feature_flags: {} })
      .mockResolvedValueOnce([{ id: "roster-1", name: "SA24D", students: [] }])
      .mockResolvedValueOnce([{ id: "template-1", name: "Sal 101", seats: [], fixtures: [] }]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue({
      draft: {
        id: "draft-1",
        roster_id: "roster-1",
        template_id: "template-1",
        lesson_mode_id: "group_work",
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
});
