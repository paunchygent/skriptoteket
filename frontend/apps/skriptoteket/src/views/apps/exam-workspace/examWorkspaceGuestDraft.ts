/**
 * Exam workspace guest draft and undo history.
 *
 * Domain purpose:
 *   The one exam draft a guest edits without signing in, modelled as a pure
 *   transition over an in-memory record. A guest's exam lives only in this
 *   browser: the draft keeps the last saved copy, the bounded undo history
 *   and the snapshot the editor stands on, and mirrors the server's
 *   document + history semantics step for step so the same workspace UI can
 *   run on either side of the sign-in boundary.
 *
 *   The record deliberately holds no picture bytes. `asset_ids` names the
 *   declared pictures whose bytes the browser storage holds beside the
 *   draft; the storage module owns those bytes.
 *
 * Relationships:
 *   - Mirrors `exam_workspace_history.py` (cursor, baseline, steps, bounded
 *     history response) and the handlers in `handlers/exam_workspace_undo_steps.py`
 *     (open, branch after undo, the stored step that also updates the saved
 *     copy, the position move that writes a step to the saved copy).
 *   - Uses the transport types of `api/examWorkspace.ts`; imports the client
 *     save rules so a refused document is refused here with the same copy the
 *     server's 422 would name.
 *   - Persisted by `examWorkspaceGuestDraftStorage.ts` and wrapped into the
 *     guest workspace store in `examWorkspaceGuestStore.ts`. No I/O and no
 *     network here.
 */

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceHistory,
  ExamWorkspaceHistoryDocument,
  ExamWorkspaceUndoStep,
  NativeExamDocument,
} from "../../../api/examWorkspace";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";

/** The server keeps at most this many snapshots after the import baseline. */
export const GUEST_MAX_RETAINED_UNDO_STEPS = 100;

/** Every id and timestamp the draft creates comes from this injected source. */
export type ExamWorkspaceGuestDraftIdSource = {
  uuid(): string;
  now(): string;
};

export type ExamWorkspaceGuestDraftStep = {
  step_id: string;
  document: NativeExamDocument;
};

export type ExamWorkspaceGuestDraft = {
  /** The exam document's identity; the same value a saved workspace file names. */
  lineage_id: string;
  saved_document: NativeExamDocument;
  saved_at: string;
  /** Concurrency token: rotates on every write, never a step to stand on. */
  cursor: string;
  baseline: ExamWorkspaceGuestDraftStep;
  steps: ExamWorkspaceGuestDraftStep[];
  /** The retained snapshot the editor stands on. */
  position_step_id: string;
  asset_ids: string[];
  /** The parser's import notes; the workspace shows them exactly like a teacher's. */
  notes: ExamWorkspaceDocumentResponse["notes"];
};

export type ExamWorkspaceGuestUndoStepOutcome =
  | { kind: "ok"; draft: ExamWorkspaceGuestDraft; step: ExamWorkspaceUndoStep }
  | { kind: "conflict" }
  | { kind: "refused"; copy: string };

export type ExamWorkspaceGuestHistoryStepOutcome =
  | { kind: "ok"; step: ExamWorkspaceHistoryDocument }
  | { kind: "not_found" };

export type ExamWorkspaceGuestHistoryPositionOutcome =
  | { kind: "ok"; draft: ExamWorkspaceGuestDraft; step: ExamWorkspaceUndoStep }
  | { kind: "conflict" }
  | { kind: "not_found" }
  | { kind: "refused"; copy: string };

function withRevision(document: NativeExamDocument, revision: number): NativeExamDocument {
  return { ...document, revision };
}

function snapshots(draft: ExamWorkspaceGuestDraft): ExamWorkspaceGuestDraftStep[] {
  return [draft.baseline, ...draft.steps];
}

function snapshotById(
  draft: ExamWorkspaceGuestDraft,
  stepId: string,
): ExamWorkspaceGuestDraftStep | null {
  return snapshots(draft).find((step) => step.step_id === stepId) ?? null;
}

function snapshotIds(draft: ExamWorkspaceGuestDraft): string[] {
  return snapshots(draft).map((step) => step.step_id);
}

/** `history_response(history)` in `exam_workspace_history.py`. */
export function guestHistory(draft: ExamWorkspaceGuestDraft): ExamWorkspaceHistory {
  return {
    baseline_step_id: draft.baseline.step_id,
    cursor: draft.cursor,
    position_step_id: draft.position_step_id,
    step_ids: draft.steps.map((step) => step.step_id),
  };
}

/**
 * A fresh guest draft: the imported document is both the saved copy and the
 * baseline snapshot, exactly as the server creates a new exam's history with
 * the lineage id as its baseline step (`exam_workspace_document_store.py`
 * lines 216-225). The document's declared pictures are the stored asset ids,
 * and the parser's import notes travel with the exam like the container's.
 */
export function newGuestDraft(
  document: NativeExamDocument,
  ids: ExamWorkspaceGuestDraftIdSource,
  notes: ExamWorkspaceDocumentResponse["notes"],
): ExamWorkspaceGuestDraft {
  const baselineStepId = document.document_id;
  return {
    asset_ids: document.assets.map((asset) => asset.asset_id),
    baseline: { document, step_id: baselineStepId },
    cursor: baselineStepId,
    lineage_id: document.document_id,
    notes,
    position_step_id: baselineStepId,
    saved_at: ids.now(),
    saved_document: document,
    steps: [],
  };
}

/**
 * The response the server returns when the exam is opened
 * (`GetExamWorkspaceDocumentHandler`): the position snapshot's document with
 * the saved revision, the durable saved copy, the summary, the cursor, no
 * conversion (a guest never has one), and the draft's import notes. A guest's
 * title verdict is computed by the viewer from public command responses and
 * export refusals only, so no export blockers are invented here.
 */
export function guestDocumentResponse(
  draft: ExamWorkspaceGuestDraft,
): ExamWorkspaceDocumentResponse {
  const position = snapshotById(draft, draft.position_step_id);
  if (position === null) {
    throw new Error("The guest draft's position snapshot is missing from its history.");
  }
  const saved = draft.saved_document;
  return {
    conversion: null,
    document: withRevision(position.document, saved.revision),
    export_blockers: [],
    history_cursor: draft.cursor,
    notes: draft.notes,
    saved_document: saved,
    summary: {
      course_key: saved.header.course?.key ?? null,
      lineage_id: draft.lineage_id,
      name: saved.title,
      saved_at: draft.saved_at,
      title: saved.title,
      vault_file_id: draft.lineage_id,
      version: saved.revision,
    },
  };
}

/**
 * Store one undo step. The cursor guard and the branch/retention rules are
 * `StoreExamWorkspaceUndoStepHandler` lines 63-96: a stale cursor is a
 * conflict, a new step follows the position (or `afterStepId`) and drops
 * every later redo step, and only the newest 100 steps are kept. The stored
 * step also updates the saved draft in the same write, as the server's step
 * store overwrites the exam file: the stored snapshot takes the saved
 * revision + 1, and the saved copy and time follow it. A document the save
 * rules refuse can never be a step, so it is refused with the same copy a
 * 422 would carry.
 */
export function storeGuestUndoStep(
  draft: ExamWorkspaceGuestDraft,
  request: {
    expectedCursor: string;
    document: NativeExamDocument;
    afterStepId: string | null;
  },
  ids: ExamWorkspaceGuestDraftIdSource,
): ExamWorkspaceGuestUndoStepOutcome {
  if (draft.cursor !== request.expectedCursor) {
    return { kind: "conflict" };
  }
  const document = withRevision(request.document, draft.saved_document.revision + 1);
  const refusalCopy = examWorkspaceSaveRefusalCopy(document);
  if (refusalCopy !== null) {
    return { kind: "refused", copy: refusalCopy };
  }
  const after = request.afterStepId ?? draft.position_step_id;
  const idsInHistory = snapshotIds(draft);
  const afterIndex = idsInHistory.indexOf(after);
  if (afterIndex < 0) {
    return { kind: "conflict" };
  }
  const stepId = ids.uuid();
  const steps = [
    ...draft.steps.slice(0, afterIndex),
    { document, step_id: stepId },
  ].slice(-GUEST_MAX_RETAINED_UNDO_STEPS);
  const nextDraft: ExamWorkspaceGuestDraft = {
    ...draft,
    cursor: stepId,
    position_step_id: stepId,
    saved_at: ids.now(),
    saved_document: document,
    steps,
  };
  return {
    kind: "ok",
    draft: nextDraft,
    step: {
      document,
      export_blockers: [],
      history: guestHistory(nextDraft),
    },
  };
}

/**
 * Read one history step. The server's read handler returns the snapshot with
 * the saved revision (`SaveExamWorkspaceDocumentHandler.history_step` lines
 * 422-443) and leaves the history's stored position alone: only a write moves
 * it. The guest draft mirrors that here, so reading a step never changes
 * `position_step_id`; the caller stands on the returned snapshot by sending
 * it as `after_step_id` on its next write, exactly what the signed-in
 * editor's local position does.
 */
export function guestHistoryStep(
  draft: ExamWorkspaceGuestDraft,
  stepId: string,
): ExamWorkspaceGuestHistoryStepOutcome {
  const snapshot = snapshotById(draft, stepId);
  if (snapshot === null) {
    return { kind: "not_found" };
  }
  return {
    kind: "ok",
    step: {
      document: withRevision(snapshot.document, draft.saved_document.revision),
      step_id: stepId,
    },
  };
}

/**
 * Move the draft to a retained step: guest Ångra and Gör om. The server's
 * position move (`MoveExamWorkspaceHistoryPositionRequest`) sets the
 * editor's snapshot and writes that snapshot's document to the exam file
 * without a new step; the replica mirrors it by moving the position and the
 * saved copy to the snapshot. A stale cursor is a conflict, an unknown step
 * is not found, and a refused snapshot keeps the draft. Reading never moves
 * the draft; only this move and a store do.
 */
export function moveGuestHistoryPosition(
  draft: ExamWorkspaceGuestDraft,
  request: {
    expectedCursor: string;
    stepId: string;
  },
  ids: ExamWorkspaceGuestDraftIdSource,
): ExamWorkspaceGuestHistoryPositionOutcome {
  if (draft.cursor !== request.expectedCursor) {
    return { kind: "conflict" };
  }
  const snapshot = snapshotById(draft, request.stepId);
  if (snapshot === null) {
    return { kind: "not_found" };
  }
  const document = withRevision(snapshot.document, draft.saved_document.revision + 1);
  const refusalCopy = examWorkspaceSaveRefusalCopy(document);
  if (refusalCopy !== null) {
    return { kind: "refused", copy: refusalCopy };
  }
  const nextDraft: ExamWorkspaceGuestDraft = {
    ...draft,
    cursor: ids.uuid(),
    position_step_id: request.stepId,
    saved_at: ids.now(),
    saved_document: document,
    steps: draft.steps,
  };
  return {
    kind: "ok",
    draft: nextDraft,
    step: {
      document,
      export_blockers: [],
      history: guestHistory(nextDraft),
    },
  };
}

const GUEST_SAVED_TIME = new Intl.DateTimeFormat("sv-SE", {
  hour: "2-digit",
  minute: "2-digit",
});

/**
 * The guest save status the header shows after a store:
 * `Sparat i webbläsaren HH:MM`. The guest-side counterpart of the server
 * path's `Sparat HH:MM` status (unit K45): the view renders this string for
 * a guest exam where the server path renders its own.
 */
export function examWorkspaceGuestSaveStatus(savedAt: string): string {
  const at = new Date(savedAt);
  if (Number.isNaN(at.getTime())) {
    return "Sparat i webbläsaren";
  }
  return `Sparat i webbläsaren ${GUEST_SAVED_TIME.format(at)}`;
}
