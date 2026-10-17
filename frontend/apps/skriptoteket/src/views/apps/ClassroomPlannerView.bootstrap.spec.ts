/** Root planner view: bootstrap. */

import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  clientMocks,
  stateMocks,
  flushPromises,
  resetPlannerViewState,
} from "./ClassroomPlannerView.test-support";
import ClassroomPlannerView from "./ClassroomPlannerView.vue";
import type { ClassWorkspaceSummary } from "./classroomPlannerTypes";

describe("ClassroomPlannerView: bootstrap", () => {
  beforeEach(resetPlannerViewState);

  it("keeps a stable centered desktop shell when mounted inside a flex host", async () => {
    clientMocks.apiGet.mockResolvedValue([]);
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);
    const wrapper = mount(ClassroomPlannerView, {
      global: {
        plugins: [createPinia()],
      },
    });

    expect(wrapper.classes()).toContain("w-full");
    expect(wrapper.classes()).toContain("max-w-[90rem]");
    expect(wrapper.classes()).toContain("self-center");
    expect(wrapper.classes()).not.toContain("mx-auto");
    await flushPromises();
    wrapper.unmount();
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

  it("shows fallback copy instead of raw runtime errors during bootstrap", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    clientMocks.apiGet.mockRejectedValueOnce(
      new TypeError("Cannot read properties of undefined (reading 'map')"),
    );
    stateMocks.plannerState.getResumableDraft.mockResolvedValue(null);

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

    expect(wrapper.text()).toContain("Kunde inte ladda Klassrumskartan.");
    expect(wrapper.text()).not.toContain("Cannot read properties of undefined");
    expect(consoleError).toHaveBeenCalledOnce();

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
});
