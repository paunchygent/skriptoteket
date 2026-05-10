/**
 * Classroom planner guest draft history actions.
 *
 * Purpose:
 *   Keep browser-snapshot undo/redo orchestration separate from guest session
 *   assembly while preserving the current visible draft revision.
 *
 * Relationships:
 *   - consumed by `classroomPlannerGuestDraftSession.ts`
 *   - delegates snapshot storage to `classroomPlannerGuestDraftHistory.ts`
 *   - uses state support to rehydrate visible planner refs after history moves
 */

import type { ComputedRef, Ref } from "vue";

import type { DraftWorkspaceResponse, PlanDraft } from "./classroomPlannerTypes";
import type { createClassroomPlannerGuestDraftHistory } from "./classroomPlannerGuestDraftHistory";
import type { createClassroomPlannerStateSupport } from "./classroomPlannerStateSupport";
import type { useDraftPersistenceLane } from "./useDraftPersistenceLane";

type DraftLane = Pick<ReturnType<typeof useDraftPersistenceLane>, "markDirty">;
type GuestHistory = ReturnType<typeof createClassroomPlannerGuestDraftHistory>;
type StateSupport = Pick<
  ReturnType<typeof createClassroomPlannerStateSupport>,
  "applyWorkspace" | "syncVisibleSessionBindings"
>;

type DraftKind = "grouping" | "seating";
type HistoryDirection = "undo" | "redo";

export function createClassroomPlannerGuestDraftHistoryActions(options: {
  draft: Ref<PlanDraft | null>;
  isWorkspaceBusy: ComputedRef<boolean>;
  historyActionInFlight: Ref<boolean>;
  guestHistory: GuestHistory;
  stateSupport: StateSupport;
  draftLane: DraftLane;
  syncGuestHistoryStatus: () => void;
  replaceCurrentGuestHistoryWorkspace: () => void;
}) {
  async function noopHistoryAction(): Promise<void> {
    return;
  }

  function buildHistoryWorkspace(workspace: DraftWorkspaceResponse): DraftWorkspaceResponse {
    return {
      ...workspace,
      draft: {
        ...workspace.draft,
        revision: options.draft.value?.revision ?? workspace.draft.revision,
        last_opened_at: options.draft.value?.last_opened_at ?? workspace.draft.last_opened_at,
      },
    };
  }

  async function applyGuestHistoryAction(direction: HistoryDirection): Promise<void> {
    if (!options.draft.value || options.isWorkspaceBusy.value) {
      return;
    }

    options.historyActionInFlight.value = true;
    try {
      const historyWorkspace = direction === "undo"
        ? options.guestHistory.undo(options.draft.value.id)
        : options.guestHistory.redo(options.draft.value.id);
      if (!historyWorkspace) {
        options.syncGuestHistoryStatus();
        return;
      }

      options.stateSupport.applyWorkspace(buildHistoryWorkspace(historyWorkspace));
      options.replaceCurrentGuestHistoryWorkspace();
      options.stateSupport.syncVisibleSessionBindings();
      options.draftLane.markDirty();
    } finally {
      options.historyActionInFlight.value = false;
    }
  }

  function createScopedHistoryAction(draftKind: DraftKind, direction: HistoryDirection) {
    return async () => {
      if (options.draft.value?.draft_kind !== draftKind) {
        return;
      }
      await applyGuestHistoryAction(direction);
    };
  }

  return {
    noopHistoryAction,
    undoGroupingDraft: createScopedHistoryAction("grouping", "undo"),
    redoGroupingDraft: createScopedHistoryAction("grouping", "redo"),
    undoSeatingDraft: createScopedHistoryAction("seating", "undo"),
    redoSeatingDraft: createScopedHistoryAction("seating", "redo"),
  };
}
