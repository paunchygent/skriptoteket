/**
 * Classroom planner guest workspace shell tests.
 *
 * These tests verify that the guest shell keeps the visible workspace lane in
 * sync with the requested planner mode and the hydrated draft kind while
 * switching between grouping and seating.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick, reactive, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import ClassroomPlannerGuestWorkspaceShell from "./ClassroomPlannerGuestWorkspaceShell.vue";
import { provideClassroomState, type ClassroomStateLike } from "./useClassroomState";

vi.mock("../../components/help/useHelp", () => ({
  useHelp: () => ({
    setHelpContext: vi.fn(),
    clearHelpContext: vi.fn(),
  }),
}));

function mountGuestWorkspaceShellHarness() {
  const initialView = ref<"groups" | "seats">("seats");
  const plannerState = reactive({
    draft: {
      id: "draft-seating-1",
      draft_kind: "seating",
    },
    roster: {
      id: "roster-1",
      name: "SA24D",
    },
    template: {
      id: "template-1",
      name: "Sal 101",
    },
    plannerStatusLabel: null,
    plannerStatusMessage: null,
    plannerStatusTone: "neutral",
    plannerConflictMessage: null,
    reloadActiveWorkspace: vi.fn(),
  }) as unknown as ClassroomStateLike;

  const Harness = defineComponent({
    components: {
      ClassroomPlannerGuestWorkspaceShell,
    },
    setup() {
      provideClassroomState(plannerState);
      return {
        initialView,
      };
    },
    template: `
      <ClassroomPlannerGuestWorkspaceShell
        :available-rosters="[{ id: 'roster-1', name: 'SA24D', students: [] }]"
        :available-templates="[{ id: 'template-1', name: 'Sal 101', grid_cols: 4, grid_rows: 4, seats: [], fixtures: [] }]"
        selected-roster-id="roster-1"
        selected-template-id="template-1"
        :initial-view="initialView"
      />
    `,
  });

  const wrapper = mount(Harness, {
    global: {
      stubs: {
        PlannerTopPanel: {
          props: ["modeValue", "seatingDisabledReason", "contextLabel"],
          template: `
            <div
              data-test='planner-top-panel-mode'
              :data-seating-disabled-reason="seatingDisabledReason ?? ''"
              :data-context-label="contextLabel ?? ''"
            >
              {{ modeValue }}
            </div>
          `,
        },
        PlannerGroupingWorkspaceToolbar: {
          template: "<div data-test='grouping-toolbar-stub' />",
        },
        PlannerGroupingWorkspacePane: {
          template: "<div data-test='grouping-pane-stub' />",
        },
        PlannerSeatingWorkspaceToolbar: {
          template: "<div data-test='seating-toolbar-stub' />",
        },
        PlannerSeatingWorkspacePane: {
          template: "<div data-test='seating-pane-stub' />",
        },
      },
    },
  });

  return {
    wrapper,
    initialView,
    plannerState,
  };
}

describe("ClassroomPlannerGuestWorkspaceShell", () => {
  it("uses the shared sticky toolbar shell contract for both guest workspace modes", async () => {
    const { wrapper, initialView, plannerState } = mountGuestWorkspaceShellHarness();

    expect(
      wrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="seats"]').classes(),
    ).toEqual(
      expect.arrayContaining(["sticky", "top-0", "z-20"]),
    );
    expect(
      wrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="seats"]').classes(),
    ).not.toContain("md:-top-4");

    initialView.value = "groups";
    plannerState.draft = {
      id: "draft-grouping-1",
      draft_kind: "grouping",
    } as ClassroomStateLike["draft"];
    plannerState.template = null as ClassroomStateLike["template"];
    await nextTick();

    expect(
      wrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="groups"]').classes(),
    ).toEqual(
      expect.arrayContaining(["sticky", "top-0", "z-20"]),
    );
    expect(
      wrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="groups"]').classes(),
    ).not.toContain("md:-top-4");
  });

  it("returns to grouping after a seating-first mode switch sequence", async () => {
    const { wrapper, initialView, plannerState } = mountGuestWorkspaceShellHarness();

    expect(wrapper.find("[data-test='seating-pane-stub']").exists()).toBe(true);
    expect(wrapper.get("[data-test='planner-top-panel-mode']").text()).toBe("seating");

    initialView.value = "groups";
    await nextTick();

    expect(wrapper.find("[data-test='seating-pane-stub']").exists()).toBe(true);
    expect(wrapper.get("[data-test='planner-top-panel-mode']").text()).toBe("seating");

    plannerState.draft = {
      id: "draft-grouping-1",
      draft_kind: "grouping",
    } as ClassroomStateLike["draft"];
    plannerState.template = null as ClassroomStateLike["template"];
    await nextTick();

    expect(wrapper.find("[data-test='grouping-pane-stub']").exists()).toBe(true);
    expect(wrapper.find("[data-test='seating-pane-stub']").exists()).toBe(false);
    expect(wrapper.get("[data-test='planner-top-panel-mode']").text()).toBe("grouping");
  });

  it("keeps the seating selector enabled from grouping when overview classroom selection persists", async () => {
    const { wrapper, initialView, plannerState } = mountGuestWorkspaceShellHarness();

    initialView.value = "groups";
    await nextTick();

    plannerState.draft = {
      id: "draft-grouping-1",
      draft_kind: "grouping",
    } as ClassroomStateLike["draft"];
    plannerState.template = null as ClassroomStateLike["template"];
    await nextTick();

    expect(wrapper.get("[data-test='planner-top-panel-mode']").text()).toBe("grouping");
    expect(
      wrapper.get("[data-test='planner-top-panel-mode']").attributes("data-seating-disabled-reason"),
    ).toBe("");
    expect(
      wrapper.get("[data-test='planner-top-panel-mode']").attributes("data-context-label"),
    ).toBe("Sal 101");
    expect(
      wrapper.get('[data-ui="planner-workspace-pane-shell"][data-view="groups"]').classes(),
    ).toEqual(
      expect.arrayContaining(["xl:min-h-0", "xl:max-h-full", "xl:overflow-y-auto"]),
    );
  });
});
