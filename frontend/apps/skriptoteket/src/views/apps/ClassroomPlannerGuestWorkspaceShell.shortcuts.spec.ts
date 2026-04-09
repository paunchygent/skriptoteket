/**
 * Guest workspace shell shortcut integration tests.
 *
 * These tests keep the guest-shell shortcut proof narrow and exercise the
 * real public toolbar menus without inflating the broader guest shell spec.
 */

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, reactive } from "vue";

import ClassroomPlannerGuestWorkspaceShell from "./ClassroomPlannerGuestWorkspaceShell.vue";
import { provideClassroomState } from "./useClassroomState";
import {
  createPlannerShortcutTestState,
  plannerShortcutShellStubs,
} from "./test/plannerShortcutTestHarness";

const helpMocks = vi.hoisted(() => ({
  setHelpContext: vi.fn(),
  clearHelpContext: vi.fn(),
}));

const toastMocks = vi.hoisted(() => ({
  info: vi.fn(),
  success: vi.fn(),
  warning: vi.fn(),
}));

vi.mock("../../components/help/useHelp", () => ({
  useHelp: () => helpMocks,
}));

vi.mock("../../composables/useToast", () => ({
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

function mountGuestWorkspaceShell(options: {
  initialView: "groups" | "seats";
  draftKind: "grouping" | "seating";
}) {
  const plannerState = reactive(createPlannerShortcutTestState());
  plannerState.draft = {
    ...plannerState.draft,
    draft_kind: options.draftKind,
    id: `${options.draftKind}-draft-1`,
  };

  const Harness = defineComponent({
    components: { ClassroomPlannerGuestWorkspaceShell },
    setup() {
      provideClassroomState(plannerState as never);
      return {};
    },
    template: `
      <div>
        <input data-test="shortcut-input-probe" />
        <ClassroomPlannerGuestWorkspaceShell
          :available-rosters="[{ id: 'roster-1', name: 'SA24D', students: [] }]"
          :available-templates="[{ id: 'template-1', name: 'Sal 101', seats: [{ id: 'seat-1', x: 0, y: 0, zone: null }], fixtures: [] }]"
          selected-roster-id="roster-1"
          selected-template-id="template-1"
          initial-view="${options.initialView}"
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
    plannerState,
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

describe("ClassroomPlannerGuestWorkspaceShell shortcuts", () => {
  it("routes guest grouping undo from a neutral toolbar target but ignores the same shortcut inside the real actions menu", async () => {
    const { wrapper, plannerState } = mountGuestWorkspaceShell({
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

    const menuItem = wrapper.get('[data-test="edit-grouping-roster"]');
    const blockedEvent = dispatchShortcut(menuItem.element, {
      key: "z",
      ctrlKey: true,
    });

    expect(plannerState.undoGroupingDraft).toHaveBeenCalledTimes(1);
    expect(blockedEvent.defaultPrevented).toBe(false);

    wrapper.unmount();
  });

  it("routes guest seating redo from a neutral toolbar target but ignores the same shortcut while typing in an input probe", () => {
    const { wrapper, plannerState } = mountGuestWorkspaceShell({
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
