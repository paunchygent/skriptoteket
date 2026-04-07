/**
 * Planner undo/redo shortcut composable.
 *
 * This composable owns the shared keyboard listener for planner undo/redo so
 * the authenticated and guest workspace shells can both expose shortcut
 * parity without reimplementing DOM guards in each shell.
 */

import { onMounted, onUnmounted } from "vue";

import type { PlanDraft, PlanDraftKind } from "./classroomPlannerTypes";

type PlannerUndoRedoShortcutState = {
  draft: PlanDraft | null;
  canUndo: boolean;
  canRedo: boolean;
  undoGroupingDraft: () => Promise<void>;
  redoGroupingDraft: () => Promise<void>;
  undoSeatingDraft: () => Promise<void>;
  redoSeatingDraft: () => Promise<void>;
};

type UsePlannerUndoRedoShortcutsOptions = {
  plannerState: PlannerUndoRedoShortcutState;
  isEnabled?: () => boolean;
};

function resolvesUndoRedoTarget(target: EventTarget | null): Element | null {
  if (target instanceof Element) {
    return target;
  }
  return null;
}

function isEditableTarget(target: Element | null): boolean {
  if (!target) {
    return false;
  }
  if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
    return true;
  }
  if (target instanceof HTMLSelectElement) {
    return true;
  }
  if (target.closest("[contenteditable='true']")) {
    return true;
  }
  if (target.closest("[role='textbox']")) {
    return true;
  }
  return target.matches("[contenteditable='true']");
}

function isMenuTarget(target: Element | null): boolean {
  if (!target) {
    return false;
  }
  return target.closest("[role='menu']") !== null;
}

function resolveShortcutDraftKind(draft: PlanDraft | null): PlanDraftKind | null {
  return draft?.draft_kind ?? null;
}

export function usePlannerUndoRedoShortcuts(options: UsePlannerUndoRedoShortcutsOptions): void {
  function handleKeydown(event: KeyboardEvent): void {
    if (event.defaultPrevented || event.altKey) {
      return;
    }

    const target = resolvesUndoRedoTarget(event.target);
    if (isEditableTarget(target) || isMenuTarget(target)) {
      return;
    }

    const usesModifier = event.metaKey || event.ctrlKey;
    if (!usesModifier) {
      return;
    }

    if (options.isEnabled && !options.isEnabled()) {
      return;
    }

    const normalizedKey = event.key.toLowerCase();
    const wantsUndo = normalizedKey === "z" && !event.shiftKey;
    const wantsRedo = normalizedKey === "z" && event.shiftKey;
    const wantsWindowsRedo = normalizedKey === "y" && event.ctrlKey && !event.metaKey;

    if (!wantsUndo && !wantsRedo && !wantsWindowsRedo) {
      return;
    }

    const draftKind = resolveShortcutDraftKind(options.plannerState.draft);
    if (!draftKind) {
      return;
    }

    if (wantsUndo && !options.plannerState.canUndo) {
      return;
    }
    if ((wantsRedo || wantsWindowsRedo) && !options.plannerState.canRedo) {
      return;
    }

    event.preventDefault();

    if (draftKind === "grouping") {
      if (wantsUndo) {
        void options.plannerState.undoGroupingDraft();
        return;
      }
      void options.plannerState.redoGroupingDraft();
      return;
    }

    if (wantsUndo) {
      void options.plannerState.undoSeatingDraft();
      return;
    }
    void options.plannerState.redoSeatingDraft();
  }

  onMounted(() => {
    window.addEventListener("keydown", handleKeydown);
  });

  onUnmounted(() => {
    window.removeEventListener("keydown", handleKeydown);
  });
}
