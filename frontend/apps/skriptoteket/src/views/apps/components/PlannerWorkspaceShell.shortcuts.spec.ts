/**
 * Planner workspace shell shortcut integration tests.
 *
 * These tests keep the shell-level shortcut proof focused on real toolbar menu
 * interactions without growing the already-large general shell spec further.
 */

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, reactive } from "vue";

import PlannerWorkspaceShell from "./PlannerWorkspaceShell.vue";
import {
  buildPlannerShortcutWorkspaceSummary,
  createPlannerShortcutTestState,
  plannerShortcutShellStubs,
} from "../test/plannerShortcutTestHarness";

const helpMocks = vi.hoisted(() => ({
  setHelpContext: vi.fn(),
  clearHelpContext: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  info: vi.fn(),
  success: vi.fn(),
  warning: vi.fn(),
}));

const plannerStateRef = vi.hoisted(() => ({
  current: null as ReturnType<typeof createPlannerShortcutTestState> | null,
}));

vi.mock("../useClassroomState", () => ({
  useClassroomState: () => plannerStateRef.current,
}));

vi.mock("../../../components/help/useHelp", () => ({
  useHelp: () => helpMocks,
}));

vi.mock("../../../composables/useToast", () => ({
  useToast: () => toastMocks,
}));

function dispatchShortcut(target: Element, init: KeyboardEventInit): KeyboardEvent {
  const event = new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    ...init,
  });
  target.dispatchEvent(event);
  return event;
}

function mountPlannerWorkspaceShell(options: {
  initialView: "groups" | "seats";
  draftKind: "grouping" | "seating";
}) {
  plannerStateRef.current = reactive(createPlannerShortcutTestState());
  plannerStateRef.current.draft = {
    ...plannerStateRef.current.draft,
    draft_kind: options.draftKind,
    id: `${options.draftKind}-draft-1`,
  };

  const Harness = defineComponent({
    components: { PlannerWorkspaceShell },
    data() {
      return {
        initialView: options.initialView,
        workspaceSummary: buildPlannerShortcutWorkspaceSummary(),
      };
    },
    template: `
      <div>
        <input data-test="shortcut-input-probe" />
        <PlannerWorkspaceShell
          :available-rosters="[{ id: 'roster-1', name: 'SA24D', students: [] }]"
          :available-templates="[{ id: 'template-1', name: 'Sal 101', seats: [{ id: 'seat-1', x: 0, y: 0, zone: null }], fixtures: [] }]"
          selected-roster-id="roster-1"
          selected-workspace-template-id="template-1"
          :initial-view="initialView"
          :workspace-summary="workspaceSummary"
        />
      </div>
    `,
  });

  const wrapper = mount(Harness, {
    attachTo: document.body,
    global: {
      stubs: plannerShortcutShellStubs,
    },
  });

  return {
    wrapper,
    plannerState: plannerStateRef.current,
  };
}

beforeEach(() => {
  helpMocks.setHelpContext.mockReset();
  helpMocks.clearHelpContext.mockReset();
  toastMocks.info.mockReset();
  toastMocks.success.mockReset();
  toastMocks.warning.mockReset();
});

afterEach(() => {
  document.body.innerHTML = "";
});

describe("PlannerWorkspaceShell shortcuts", () => {
  it("routes grouping undo from a neutral toolbar target but ignores the same shortcut inside the real actions menu", async () => {
    const { wrapper, plannerState } = mountPlannerWorkspaceShell({
      initialView: "groups",
      draftKind: "grouping",
    });
    plannerState.canUndo = true;

    const neutralTarget = wrapper.get('[data-test="grouping-actions-menu"]');
    const allowedEvent = dispatchShortcut(neutralTarget.element, {
      key: "z",
      ctrlKey: true,
    });

    expect(plannerState.undoGroupingDraft).toHaveBeenCalledTimes(1);
    expect(allowedEvent.defaultPrevented).toBe(true);

    await neutralTarget.trigger("click");
    await nextTick();

    const menuItem = wrapper.get('[data-test="grouping-history"]');
    const blockedEvent = dispatchShortcut(menuItem.element, {
      key: "z",
      ctrlKey: true,
    });

    expect(plannerState.undoGroupingDraft).toHaveBeenCalledTimes(1);
    expect(blockedEvent.defaultPrevented).toBe(false);

    wrapper.unmount();
  });

  it("routes seating redo from a neutral toolbar target but ignores the same shortcut while typing in an input probe", () => {
    const { wrapper, plannerState } = mountPlannerWorkspaceShell({
      initialView: "seats",
      draftKind: "seating",
    });
    plannerState.canRedo = true;

    const neutralTarget = wrapper.get('[data-test="seating-actions-menu"]');
    const allowedEvent = dispatchShortcut(neutralTarget.element, {
      key: "y",
      ctrlKey: true,
    });

    expect(plannerState.redoSeatingDraft).toHaveBeenCalledTimes(1);
    expect(allowedEvent.defaultPrevented).toBe(true);

    const inputProbe = wrapper.get('[data-test="shortcut-input-probe"]');
    const blockedEvent = dispatchShortcut(inputProbe.element, {
      key: "y",
      ctrlKey: true,
    });

    expect(plannerState.redoSeatingDraft).toHaveBeenCalledTimes(1);
    expect(blockedEvent.defaultPrevented).toBe(false);

    wrapper.unmount();
  });
});
