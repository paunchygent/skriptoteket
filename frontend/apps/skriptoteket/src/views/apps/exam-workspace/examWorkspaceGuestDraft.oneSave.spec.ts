/**
 * Guest exam workspace draft: the one save model.
 *
 * Expected behavior (TASK-SKRIPT-40-04-14 behaviour item 8, unit K7):
 *   Every stored step also updates the saved draft, exactly as the server's
 *   step store overwrites the exam file in the same transaction. Ångra and
 *   Gör om move the draft to a retained step through the position move, which
 *   writes that step's document to the saved draft without storing a new
 *   step. The replica keeps 100 steps behind the baseline, and the guest
 *   status reads `Sparat i webbläsaren HH:MM` after a store.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  examWorkspaceGuestSaveStatus,
  GUEST_MAX_RETAINED_UNDO_STEPS,
  guestDocumentResponse,
  moveGuestHistoryPosition,
  newGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";

/** Any current-schema document; scenarios override only the title. */
function exam(title = "Original"): NativeExamDocument {
  return { ...buildParentDocument(), title };
}

function createIds(now = "2026-10-18T10:00:00.000Z"): ExamWorkspaceGuestDraftIdSource {
  let counter = 0;
  return {
    now: () => now,
    uuid: () => {
      counter += 1;
      return `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
    },
  };
}

function store(
  draft: ExamWorkspaceGuestDraft,
  title: string,
  ids: ExamWorkspaceGuestDraftIdSource,
  afterStepId: string | null = null,
) {
  const outcome = storeGuestUndoStep(
    draft,
    { afterStepId, document: exam(title), expectedCursor: draft.cursor },
    ids,
  );
  if (outcome.kind !== "ok") {
    throw new Error(`expected a stored step, got ${outcome.kind}`);
  }
  return outcome;
}

describe("examWorkspaceGuestDraft one save model", () => {
  it("keeps 100 steps behind the baseline behind one named limit", () => {
    expect(GUEST_MAX_RETAINED_UNDO_STEPS).toBe(100);
  });

  it("updates the saved draft on every stored step", () => {
    const ids = createIds("2026-10-18T10:05:00.000Z");
    let draft = newGuestDraft(exam(), createIds(), []);

    const outcome = store(draft, "A", ids);
    draft = outcome.draft;

    expect(draft.saved_document.title).toBe("A");
    expect(draft.saved_document.revision).toBe(2);
    expect(draft.saved_at).toBe("2026-10-18T10:05:00.000Z");
    expect(draft.steps).toHaveLength(1);
    expect(draft.steps[0]?.document.title).toBe("A");
    expect(draft.steps[0]?.document.revision).toBe(2);
    expect(guestDocumentResponse(draft).document.title).toBe("A");
    expect(guestDocumentResponse(draft).saved_document.title).toBe("A");
  });

  it("moves the draft to a retained step on undo and back on redo without a new step", () => {
    const ids = createIds();
    let draft = newGuestDraft(exam(), ids, []);
    const baselineStepId = draft.baseline.step_id;
    draft = store(draft, "A", ids).draft;
    const stepA = draft.position_step_id;
    draft = store(draft, "B", ids).draft;
    const stepB = draft.position_step_id;
    const stepCount = draft.steps.length;
    expect(draft.saved_document.title).toBe("B");

    const undone = moveGuestHistoryPosition(
      draft,
      { expectedCursor: draft.cursor, stepId: stepA },
      ids,
    );
    if (undone.kind !== "ok") {
      throw new Error(`expected a moved draft, got ${undone.kind}`);
    }
    expect(undone.draft.position_step_id).toBe(stepA);
    expect(undone.draft.saved_document.title).toBe("A");
    expect(undone.draft.steps).toHaveLength(stepCount);
    expect(guestDocumentResponse(undone.draft).document.title).toBe("A");

    const redone = moveGuestHistoryPosition(
      undone.draft,
      { expectedCursor: undone.draft.cursor, stepId: stepB },
      ids,
    );
    if (redone.kind !== "ok") {
      throw new Error(`expected a moved draft, got ${redone.kind}`);
    }
    expect(guestDocumentResponse(redone.draft).document.title).toBe("B");
    expect(redone.draft.saved_document.title).toBe("B");
    expect(redone.draft.steps).toHaveLength(stepCount);

    const toBaseline = moveGuestHistoryPosition(
      redone.draft,
      { expectedCursor: redone.draft.cursor, stepId: baselineStepId },
      ids,
    );
    if (toBaseline.kind !== "ok") {
      throw new Error(`expected a moved draft, got ${toBaseline.kind}`);
    }
    expect(guestDocumentResponse(toBaseline.draft).document.title).toBe("Original");
  });

  it("drops the oldest step once the 101st step is stored", () => {
    const ids = createIds();
    let draft = newGuestDraft(exam(), ids, []);

    for (let index = 1; index <= GUEST_MAX_RETAINED_UNDO_STEPS + 1; index += 1) {
      draft = store(draft, `Steg ${index}`, ids).draft;
    }

    expect(draft.steps).toHaveLength(GUEST_MAX_RETAINED_UNDO_STEPS);
    expect(draft.steps[0]?.document.title).toBe("Steg 2");
    expect(draft.steps[GUEST_MAX_RETAINED_UNDO_STEPS - 1]?.document.title).toBe(
      `Steg ${GUEST_MAX_RETAINED_UNDO_STEPS + 1}`,
    );
    expect(draft.position_step_id).toBe(
      draft.steps[GUEST_MAX_RETAINED_UNDO_STEPS - 1]?.step_id,
    );
  });

  it("reads the guest status as Sparat i webbläsaren HH:MM after a store", () => {
    const ids = createIds("2026-10-18T10:05:00.000Z");
    let draft = newGuestDraft(exam(), createIds(), []);
    draft = store(draft, "A", ids).draft;

    const status = examWorkspaceGuestSaveStatus(draft.saved_at);

    expect(status).toMatch(/^Sparat i webbläsaren \d{2}:\d{2}$/);
  });

  it("refuses the position move on a stale cursor, an unknown step or a refused document", () => {
    const ids = createIds();
    let draft = newGuestDraft(exam(), ids, []);
    draft = store(draft, "A", ids).draft;
    const before = structuredClone(draft);

    expect(
      moveGuestHistoryPosition(
        draft,
        { expectedCursor: "99999999-9999-4999-8999-999999999999", stepId: draft.position_step_id },
        ids,
      ),
    ).toEqual({ kind: "conflict" });
    expect(
      moveGuestHistoryPosition(
        draft,
        {
          expectedCursor: draft.cursor,
          stepId: "99999999-9999-4999-8999-999999999999",
        },
        ids,
      ),
    ).toEqual({ kind: "not_found" });
    expect(draft).toEqual(before);
  });
});
