/**
 * Classroom planner guest workspace shell tests.
 *
 * These tests verify that the guest shell keeps the shared workspace chrome,
 * exposes `Regler`, Smart, and export parity while still hiding account-only
 * history settings in the public browser-owned lane.
 */

import { mount } from "@vue/test-utils";
import { defineComponent, nextTick, reactive, ref } from "vue";
import { describe, expect, it, vi } from "vitest";

import ClassroomPlannerGuestWorkspaceShell from "./ClassroomPlannerGuestWorkspaceShell.vue";
import { PLANNER_NO_CLASSROOM_HINT } from "./plannerWorkspacePrerequisites";
import { provideClassroomState, type ClassroomStateLike } from "./useClassroomState";

vi.mock("../../components/help/useHelp", () => ({
  useHelp: () => ({
    setHelpContext: vi.fn(),
    clearHelpContext: vi.fn(),
  }),
}));

vi.mock("../../composables/useToast", () => ({
  useToast: () => ({
    info: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
  }),
}));

function mountGuestWorkspaceShellHarness(options?: {
  initialView?: "groups" | "seats" | "rules";
  selectedTemplateId?: string | null;
}) {
  const initialView = ref<"groups" | "seats" | "rules">(options?.initialView ?? "seats");
  const selectedTemplateId = ref<string | null>(options?.selectedTemplateId ?? "template-1");
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
    activeSeatingSmartTool: null,
    smartGroupingRunMessage: null,
    smartGroupingRunTone: "neutral",
    smartSeatingRunMessage: null,
    smartSeatingRunTone: "neutral",
    plannerStatusLabel: null,
    plannerStatusMessage: null,
    plannerStatusTone: "neutral",
    plannerConflictMessage: null,
    handleSeatingSmartToolStudentSelection: vi.fn(),
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
        selectedTemplateId,
      };
    },
    template: `
      <ClassroomPlannerGuestWorkspaceShell
        :available-rosters="[{ id: 'roster-1', name: 'SA24D', students: [] }]"
        :available-templates="[{ id: 'template-1', name: 'Sal 101', grid_cols: 4, grid_rows: 4, seats: [], fixtures: [] }]"
        selected-roster-id="roster-1"
        :selected-template-id="selectedTemplateId"
        :initial-view="initialView"
      />
    `,
  });

  const wrapper = mount(Harness, {
    global: {
      stubs: {
        PlannerTopPanel: {
          props: [
            "modeValue",
            "seatingDisabledReason",
            "rulesDisabledReason",
            "contextLabel",
            "showRulesOption",
          ],
          template: `
            <div
              data-test='planner-top-panel-mode'
              :data-seating-disabled-reason="seatingDisabledReason ?? ''"
              :data-rules-disabled-reason="rulesDisabledReason ?? ''"
              :data-context-label="contextLabel ?? ''"
              :data-show-rules-option="String(showRulesOption)"
            >
              {{ modeValue }}
            </div>
          `,
        },
        PlannerGroupingWorkspaceToolbar: {
          name: "PlannerGroupingWorkspaceToolbar",
          props: [
            "showHistoryAction",
            "showSmartControls",
            "smartSettingsOpen",
            "showExportActions",
          ],
          template: `
            <div
              data-test='grouping-toolbar-stub'
              :data-show-history-action="String(showHistoryAction)"
              :data-show-smart-controls="String(showSmartControls)"
              :data-smart-settings-open="String(smartSettingsOpen)"
              :data-show-export-actions="String(showExportActions)"
            />
          `,
        },
        PlannerGroupingWorkspacePane: {
          template: "<div data-test='grouping-pane-stub' />",
        },
        PlannerSeatingWorkspaceToolbar: {
          name: "PlannerSeatingWorkspaceToolbar",
          props: [
            "showHistoryAction",
            "showSmartControls",
            "smartSettingsOpen",
            "showExportActions",
          ],
          template: `
            <div
              data-test='seating-toolbar-stub'
              :data-show-history-action="String(showHistoryAction)"
              :data-show-smart-controls="String(showSmartControls)"
              :data-smart-settings-open="String(smartSettingsOpen)"
              :data-show-export-actions="String(showExportActions)"
            />
          `,
        },
        PlannerSeatingWorkspacePane: {
          template: "<div data-test='seating-pane-stub' />",
        },
        PlannerRulesWorkspacePane: {
          template: "<div data-test='rules-pane-stub' />",
        },
        PlannerGroupingSettingsDrawer: {
          name: "PlannerGroupingSettingsDrawer",
          props: ["open", "showHistorySetting"],
          template: `
            <div
              data-test='grouping-settings-drawer-stub'
              :data-open="String(open)"
              :data-show-history-setting="String(showHistorySetting)"
            />
          `,
        },
        PlannerSeatingSettingsDrawer: {
          name: "PlannerSeatingSettingsDrawer",
          props: ["open", "showHistorySetting"],
          template: `
            <div
              data-test='seating-settings-drawer-stub'
              :data-open="String(open)"
              :data-show-history-setting="String(showHistorySetting)"
            />
          `,
        },
      },
    },
  });

  return {
    wrapper,
    initialView,
    selectedTemplateId,
    plannerState,
  };
}

describe("ClassroomPlannerGuestWorkspaceShell", () => {
  it("uses the shared sticky toolbar shell contract for both guest workspace modes", async () => {
    const { wrapper, initialView, plannerState } = mountGuestWorkspaceShellHarness();

    expect(
      wrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="seats"]').classes(),
    ).toEqual(expect.arrayContaining(["planner-workspace-toolbar-shell"]));
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
    ).toEqual(expect.arrayContaining(["planner-workspace-toolbar-shell"]));
    expect(
      wrapper.get('[data-ui="planner-workspace-toolbar-shell"][data-view="groups"]').classes(),
    ).not.toContain("md:-top-4");
  });

  it("renders the dedicated rules pane when the guest controller requests Regler", () => {
    const { wrapper } = mountGuestWorkspaceShellHarness({ initialView: "rules" });

    expect(wrapper.find("[data-test='rules-pane-stub']").exists()).toBe(true);
    expect(wrapper.find("[data-test='seating-pane-stub']").exists()).toBe(false);
    expect(wrapper.get("[data-test='planner-top-panel-mode']").text()).toBe("rules");
    expect(
      wrapper.get("[data-test='planner-top-panel-mode']").attributes("data-show-rules-option"),
    ).toBe("true");
  });

  it("keeps Smart and export visible while hiding account-only history controls in the guest shell", async () => {
    const { wrapper, initialView, plannerState } = mountGuestWorkspaceShellHarness();

    expect(
      wrapper.get("[data-test='seating-toolbar-stub']").attributes("data-show-smart-controls"),
    ).toBe("true");
    expect(
      wrapper.get("[data-test='seating-toolbar-stub']").attributes("data-show-export-actions"),
    ).toBe("true");
    expect(
      wrapper.get("[data-test='seating-toolbar-stub']").attributes("data-show-history-action"),
    ).toBe("false");

    wrapper.getComponent({ name: "PlannerSeatingWorkspaceToolbar" }).vm.$emit("open-settings");
    await nextTick();

    expect(
      wrapper.get("[data-test='seating-settings-drawer-stub']").attributes("data-open"),
    ).toBe("true");
    expect(
      wrapper.get("[data-test='seating-settings-drawer-stub']").attributes(
        "data-show-history-setting",
      ),
    ).toBe("false");

    initialView.value = "groups";
    plannerState.draft = {
      id: "draft-grouping-1",
      draft_kind: "grouping",
    } as ClassroomStateLike["draft"];
    plannerState.template = null as ClassroomStateLike["template"];
    await nextTick();

    expect(
      wrapper.get("[data-test='grouping-toolbar-stub']").attributes("data-show-smart-controls"),
    ).toBe("true");
    expect(
      wrapper.get("[data-test='grouping-toolbar-stub']").attributes("data-show-export-actions"),
    ).toBe("true");
    expect(
      wrapper.get("[data-test='grouping-toolbar-stub']").attributes("data-show-history-action"),
    ).toBe("false");

    wrapper.getComponent({ name: "PlannerGroupingWorkspaceToolbar" }).vm.$emit("open-settings");
    await nextTick();

    expect(
      wrapper.get("[data-test='grouping-settings-drawer-stub']").attributes("data-open"),
    ).toBe("true");
    expect(
      wrapper.get("[data-test='grouping-settings-drawer-stub']").attributes(
        "data-show-history-setting",
      ),
    ).toBe("false");
  });

  it("disables Sittplatser when grouping no longer has a classroom context", async () => {
    const { wrapper, plannerState, selectedTemplateId } = mountGuestWorkspaceShellHarness({
      initialView: "groups",
      selectedTemplateId: "template-1",
    });

    plannerState.draft = {
      id: "draft-grouping-1",
      draft_kind: "grouping",
    } as ClassroomStateLike["draft"];
    plannerState.template = null as ClassroomStateLike["template"];
    await nextTick();

    selectedTemplateId.value = null;
    await nextTick();

    expect(
      wrapper.get("[data-test='planner-top-panel-mode']").attributes("data-seating-disabled-reason"),
    ).toBe(PLANNER_NO_CLASSROOM_HINT);
  });
});
