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

  it("ignores undo shortcuts inside editable targets", () => {
    const { wrapper, plannerState } = mountShortcutHarness({
      draftKind: "seating",
      canUndo: true,
    });

    const input = document.createElement("input");
    document.body.appendChild(input);

    const event = new KeyboardEvent("keydown", {
      key: "z",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    input.dispatchEvent(event);

    expect(plannerState.undoSeatingDraft).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);

    wrapper.unmount();
  });

  it("ignores undo shortcuts during menu-managed keyboard interactions", () => {
    const { wrapper, plannerState } = mountShortcutHarness({
      draftKind: "grouping",
      canUndo: true,
    });

    const menu = document.createElement("div");
    menu.setAttribute("role", "menu");
    const menuItem = document.createElement("button");
    menu.appendChild(menuItem);
    document.body.appendChild(menu);

    const event = new KeyboardEvent("keydown", {
      key: "z",
      metaKey: true,
      bubbles: true,
      cancelable: true,
    });
    menuItem.dispatchEvent(event);

    expect(plannerState.undoGroupingDraft).not.toHaveBeenCalled();
    expect(event.defaultPrevented).toBe(false);

    wrapper.unmount();
  });
});
