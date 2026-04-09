/**
 * Planner undo/redo shortcut composable tests.
 *
 * These tests verify that the shared planner shortcut seam routes undo/redo to
 * the active draft while refusing to hijack text-entry or menu-managed
 * keyboard interactions.
 */

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { defineComponent, reactive } from "vue";

import { usePlannerUndoRedoShortcuts } from "./usePlannerUndoRedoShortcuts";
import type { PlanDraft } from "./classroomPlannerTypes";

type ShortcutHarnessOptions = {
  draftKind: "grouping" | "seating" | null;
  canUndo?: boolean;
  canRedo?: boolean;
  isEnabled?: boolean;
};

function dispatchShortcut(
  target: Window | Element,
  init: KeyboardEventInit,
): KeyboardEvent {
  const event = new KeyboardEvent("keydown", {
    bubbles: true,
    cancelable: true,
    ...init,
  });
  target.dispatchEvent(event);
  return event;
}

function mountShortcutHarness(options: ShortcutHarnessOptions) {
  const draft: PlanDraft | null = options.draftKind
    ? {
        id: `${options.draftKind}-draft-1`,
        roster_id: "roster-1",
        draft_kind: options.draftKind,
        status: "active",
        revision: 1,
        last_opened_at: "2026-04-08T18:00:00Z",
      }
    : null;

  const plannerState = reactive({
    draft,
    canUndo: options.canUndo ?? false,
    canRedo: options.canRedo ?? false,
    undoGroupingDraft: vi.fn(async () => {}),
    redoGroupingDraft: vi.fn(async () => {}),
    undoSeatingDraft: vi.fn(async () => {}),
    redoSeatingDraft: vi.fn(async () => {}),
  });

  const Harness = defineComponent({
    setup() {
      usePlannerUndoRedoShortcuts({
        plannerState,
        isEnabled: () => options.isEnabled ?? true,
      });
      return () => null;
    },
  });

  const wrapper = mount(Harness, {
    attachTo: document.body,
  });

  return {
    wrapper,
    plannerState,
  };
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("usePlannerUndoRedoShortcuts", () => {
  it("routes Cmd/Ctrl+Z to grouping undo and Ctrl+Y to seating redo", () => {
    const grouping = mountShortcutHarness({
      draftKind: "grouping",
      canUndo: true,
    });

    const groupingEvent = new KeyboardEvent("keydown", {
      key: "z",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    window.dispatchEvent(groupingEvent);

    expect(grouping.plannerState.undoGroupingDraft).toHaveBeenCalledTimes(1);
    expect(groupingEvent.defaultPrevented).toBe(true);

    grouping.wrapper.unmount();

    const seating = mountShortcutHarness({
      draftKind: "seating",
      canRedo: true,
    });

    const seatingEvent = new KeyboardEvent("keydown", {
      key: "y",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    window.dispatchEvent(seatingEvent);

    expect(seating.plannerState.redoSeatingDraft).toHaveBeenCalledTimes(1);
    expect(seatingEvent.defaultPrevented).toBe(true);

    seating.wrapper.unmount();
  });

  it("ignores shortcuts inside editable and menu-managed targets", () => {
    const { wrapper, plannerState } = mountShortcutHarness({
      draftKind: "seating",
      canUndo: true,
      canRedo: true,
    });

    const cases = [
      {
        label: "input",
        buildTarget: () => {
          const input = document.createElement("input");
          document.body.appendChild(input);
          return input;
        },
        init: { key: "z", ctrlKey: true },
      },
      {
        label: "textarea",
        buildTarget: () => {
          const textarea = document.createElement("textarea");
          document.body.appendChild(textarea);
          return textarea;
        },
        init: { key: "z", ctrlKey: true },
      },
      {
        label: "select",
        buildTarget: () => {
          const select = document.createElement("select");
          document.body.appendChild(select);
          return select;
        },
        init: { key: "z", ctrlKey: true },
      },
      {
        label: "contenteditable host",
        buildTarget: () => {
          const editable = document.createElement("div");
          editable.setAttribute("contenteditable", "true");
          editable.contentEditable = "true";
          document.body.appendChild(editable);
          return editable;
        },
        init: { key: "z", ctrlKey: true },
      },
      {
        label: "contenteditable descendant",
        buildTarget: () => {
          const editable = document.createElement("div");
          editable.setAttribute("contenteditable", "true");
          editable.contentEditable = "true";
          const child = document.createElement("span");
          editable.appendChild(child);
          document.body.appendChild(editable);
          return child;
        },
        init: { key: "z", ctrlKey: true },
      },
      {
        label: "textbox role",
        buildTarget: () => {
          const textbox = document.createElement("div");
          textbox.setAttribute("role", "textbox");
          document.body.appendChild(textbox);
          return textbox;
        },
        init: { key: "z", ctrlKey: true },
      },
      {
        label: "menu item",
        buildTarget: () => {
          const menu = document.createElement("div");
          menu.setAttribute("role", "menu");
          const menuItem = document.createElement("button");
          menu.appendChild(menuItem);
          document.body.appendChild(menu);
          return menuItem;
        },
        init: { key: "y", ctrlKey: true },
      },
    ] as const;

    for (const testCase of cases) {
      const target = testCase.buildTarget();
      const event = dispatchShortcut(target, testCase.init);

      expect(
        plannerState.undoSeatingDraft,
        `${testCase.label}: expected seating undo to stay untouched`,
      ).not.toHaveBeenCalled();
      expect(
        plannerState.redoSeatingDraft,
        `${testCase.label}: expected seating redo to stay untouched`,
      ).not.toHaveBeenCalled();
      expect(
        event.defaultPrevented,
        `${testCase.label}: expected planner shortcut listener to stay inert`,
      ).toBe(false);
    }

    wrapper.unmount();
  });

  it("ignores shortcuts that are already prevented", () => {
    const prevented = mountShortcutHarness({
      draftKind: "grouping",
      canUndo: true,
    });
    const preventedEvent = new KeyboardEvent("keydown", {
      key: "z",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    preventedEvent.preventDefault();
    window.dispatchEvent(preventedEvent);

    expect(prevented.plannerState.undoGroupingDraft).not.toHaveBeenCalled();
    prevented.wrapper.unmount();
  });

  it("ignores shortcuts when the seam is disabled or no draft is active", () => {
    const disabled = mountShortcutHarness({
      draftKind: "grouping",
      canUndo: true,
      isEnabled: false,
    });
    const disabledEvent = dispatchShortcut(window, { key: "z", ctrlKey: true });
    expect(disabled.plannerState.undoGroupingDraft).not.toHaveBeenCalled();
    expect(disabledEvent.defaultPrevented).toBe(false);
    disabled.wrapper.unmount();

    const noDraft = mountShortcutHarness({
      draftKind: null,
      canUndo: true,
    });
    const noDraftEvent = dispatchShortcut(window, { key: "z", ctrlKey: true });
    expect(noDraft.plannerState.undoGroupingDraft).not.toHaveBeenCalled();
    expect(noDraftEvent.defaultPrevented).toBe(false);
    noDraft.wrapper.unmount();
  });

  it("ignores shortcuts when the active draft cannot undo or redo", () => {
    const cannotUndo = mountShortcutHarness({
      draftKind: "grouping",
      canUndo: false,
    });
    const cannotUndoEvent = dispatchShortcut(window, { key: "z", metaKey: true });
    expect(cannotUndo.plannerState.undoGroupingDraft).not.toHaveBeenCalled();
    expect(cannotUndoEvent.defaultPrevented).toBe(false);
    cannotUndo.wrapper.unmount();

    const cannotRedo = mountShortcutHarness({
      draftKind: "seating",
      canRedo: false,
    });
    const cannotRedoEvent = dispatchShortcut(window, { key: "y", ctrlKey: true });
    expect(cannotRedo.plannerState.redoSeatingDraft).not.toHaveBeenCalled();
    expect(cannotRedoEvent.defaultPrevented).toBe(false);
    cannotRedo.wrapper.unmount();
  });
});
