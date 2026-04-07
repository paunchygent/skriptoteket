/**
 * Classroom planner guest draft history helper.
 *
 * This module owns one small browser-session-only undo/redo stack for guest
 * planner drafts. It keeps history state local to the public lane so the
 * guest session can expose toolbar and shortcut parity without reopening the
 * authenticated draft-history boundary.
 */

import type { DraftWorkspaceResponse } from "./classroomPlannerTypes";
import { mapDraftWorkspaceToGuestSnapshot } from "./classroomPlannerGuestSnapshotMapping";

type GuestDraftHistoryStatus = {
  can_undo: boolean;
  can_redo: boolean;
};

type GuestDraftHistoryEntry = {
  fingerprint: string;
  workspace: DraftWorkspaceResponse;
};

type GuestDraftHistoryState = {
  past: GuestDraftHistoryEntry[];
  current: GuestDraftHistoryEntry;
  future: GuestDraftHistoryEntry[];
};

function cloneWorkspace(workspace: DraftWorkspaceResponse): DraftWorkspaceResponse {
  return {
    draft: { ...workspace.draft },
    roster: {
      ...workspace.roster,
      students: workspace.roster.students.map((student) => ({ ...student })),
    },
    template: workspace.template
      ? {
          ...workspace.template,
          seats: workspace.template.seats.map((seat) => ({ ...seat })),
          fixtures: workspace.template.fixtures.map((fixture) => ({ ...fixture })),
        }
      : null,
    groups: workspace.groups.map((group) => ({ ...group })),
    group_assignments: workspace.group_assignments.map((assignment) => ({ ...assignment })),
    seat_assignments: workspace.seat_assignments.map((assignment) => ({ ...assignment })),
    history_status: {
      can_undo: false,
      can_redo: false,
    },
  };
}

function createHistoryEntry(workspace: DraftWorkspaceResponse): GuestDraftHistoryEntry {
  return {
    fingerprint: mapDraftWorkspaceToGuestSnapshot(workspace).fingerprint,
    workspace: cloneWorkspace(workspace),
  };
}

function buildHistoryStatus(state: GuestDraftHistoryState | null): GuestDraftHistoryStatus {
  if (!state) {
    return {
      can_undo: false,
      can_redo: false,
    };
  }
  return {
    can_undo: state.past.length > 0,
    can_redo: state.future.length > 0,
  };
}

export function createClassroomPlannerGuestDraftHistory() {
  const histories = new Map<string, GuestDraftHistoryState>();

  function getState(draftId: string | null): GuestDraftHistoryState | null {
    if (!draftId) {
      return null;
    }
    return histories.get(draftId) ?? null;
  }

  function bindWorkspace(workspace: DraftWorkspaceResponse): void {
    const nextEntry = createHistoryEntry(workspace);
    const currentState = histories.get(workspace.draft.id);
    if (!currentState) {
      histories.set(workspace.draft.id, {
        past: [],
        current: nextEntry,
        future: [],
      });
      return;
    }

    if (currentState.current.fingerprint === nextEntry.fingerprint) {
      currentState.current = nextEntry;
      return;
    }

    histories.set(workspace.draft.id, {
      past: [],
      current: nextEntry,
      future: [],
    });
  }

  function replaceCurrentWorkspace(workspace: DraftWorkspaceResponse): void {
    const nextEntry = createHistoryEntry(workspace);
    const currentState = histories.get(workspace.draft.id);
    if (!currentState) {
      histories.set(workspace.draft.id, {
        past: [],
        current: nextEntry,
        future: [],
      });
      return;
    }

    currentState.current = nextEntry;
  }

  function captureWorkspace(workspace: DraftWorkspaceResponse): void {
    const nextEntry = createHistoryEntry(workspace);
    const currentState = histories.get(workspace.draft.id);
    if (!currentState) {
      histories.set(workspace.draft.id, {
        past: [],
        current: nextEntry,
        future: [],
      });
      return;
    }

    if (currentState.current.fingerprint === nextEntry.fingerprint) {
      currentState.current = nextEntry;
      return;
    }

    currentState.past.push(currentState.current);
    currentState.current = nextEntry;
    currentState.future = [];
  }

  function undo(draftId: string): DraftWorkspaceResponse | null {
    const currentState = histories.get(draftId);
    if (!currentState || currentState.past.length === 0) {
      return null;
    }

    const previousEntry = currentState.past.pop();
    if (!previousEntry) {
      return null;
    }
    currentState.future.push(currentState.current);
    currentState.current = previousEntry;
    return cloneWorkspace(previousEntry.workspace);
  }

  function redo(draftId: string): DraftWorkspaceResponse | null {
    const currentState = histories.get(draftId);
    if (!currentState || currentState.future.length === 0) {
      return null;
    }

    const nextEntry = currentState.future.pop();
    if (!nextEntry) {
      return null;
    }
    currentState.past.push(currentState.current);
    currentState.current = nextEntry;
    return cloneWorkspace(nextEntry.workspace);
  }

  function getHistoryStatus(draftId: string | null): GuestDraftHistoryStatus {
    return buildHistoryStatus(getState(draftId));
  }

  return {
    bindWorkspace,
    replaceCurrentWorkspace,
    captureWorkspace,
    undo,
    redo,
    getHistoryStatus,
  };
}
