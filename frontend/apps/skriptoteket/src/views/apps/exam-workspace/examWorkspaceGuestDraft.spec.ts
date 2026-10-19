/**
 * Exam workspace guest draft and undo history.
 *
 * Expected behavior:
 *   The browser draft reproduces the server's exam history exactly: the same
 *   cursor guard, branch-after-undo, ten-step retention, Spara revision and
 *   saved-copy retention. A stale cursor or revision changes nothing, a
 *   refused document never becomes a step, reading a step leaves the stored
 *   position alone (only a write moves it), and every created id and
 *   timestamp comes from the injected source.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import {
  guestDocumentResponse,
  guestHistory,
  guestHistoryStep,
  newGuestDraft,
  saveGuestDraft,
  storeGuestUndoStep,
  type ExamWorkspaceGuestDraft,
  type ExamWorkspaceGuestDraftIdSource,
} from "./examWorkspaceGuestDraft";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";

const DOCUMENT_ID = "00000000-0000-4000-8000-000000000001";
const NOW = "2026-10-18T10:00:00.000Z";

/** Any current-schema document; scenarios override only the title. */
function exam(title = "Original"): NativeExamDocument {
  return { ...buildParentDocument(), title };
}

function pictureExam(): NativeExamDocument {
  return {
    ...exam(),
    assets: [
      {
        asset_id: "asset_001",
        byte_length: 4,
        height: 1,
        media_type: "image/png",
        sha256: "a".repeat(64),
        width: 1,
      },
    ],
    instructions: [
      { heading_level: null, segments: [{ asset_id: "asset_001", kind: "asset" }] },
    ],
  };
}

function titled(document: NativeExamDocument, title: string): NativeExamDocument {
  return { ...document, title };
}

function refusedExam(): NativeExamDocument {
  const document = exam("Refused");
  return { ...document, items: [{ ...document.items[0], points: -1 }] };
}

function createIds(): { ids: ExamWorkspaceGuestDraftIdSource; issued: string[] } {
  let counter = 0;
  const issued: string[] = [];
  return {
    issued,
    ids: {
      now: () => NOW,
      uuid: () => {
        counter += 1;
        const value = `10000000-0000-4000-8000-${String(counter).padStart(12, "0")}`;
        issued.push(value);
        return value;
      },
    },
  };
}

function store(
  draft: ExamWorkspaceGuestDraft,
  document: NativeExamDocument,
  ids: ExamWorkspaceGuestDraftIdSource,
  afterStepId: string | null = null,
) {
  const outcome = storeGuestUndoStep(
    draft,
    { afterStepId, document, expectedCursor: draft.cursor },
    ids,
  );
  if (outcome.kind !== "ok") {
    throw new Error(`expected a stored step, got ${outcome.kind}`);
  }
  return outcome;
}

describe("examWorkspaceGuestDraft", () => {
  it("derives the stored asset ids from the document's declared pictures", () => {
    const { ids } = createIds();

    expect(newGuestDraft(pictureExam(), ids).asset_ids).toEqual(["asset_001"]);
  });

  it("creates a fresh draft on the document's baseline with ids from the injected source", () => {
    const { ids, issued } = createIds();

    const draft = newGuestDraft(exam(), ids);

    expect(issued).toEqual([]);
    expect(draft.lineage_id).toBe(DOCUMENT_ID);
    expect(draft.baseline.step_id).toBe(DOCUMENT_ID);
    expect(draft.baseline.document).toBe(draft.saved_document);
    expect(draft.position_step_id).toBe(DOCUMENT_ID);
    expect(draft.cursor).toBe(DOCUMENT_ID);
    expect(draft.steps).toEqual([]);
    expect(draft.saved_at).toBe(NOW);
    expect(guestHistory(draft)).toEqual({
      baseline_step_id: DOCUMENT_ID,
      cursor: DOCUMENT_ID,
      position_step_id: DOCUMENT_ID,
      step_ids: [],
    });
  });

  it("keeps only the newest ten steps after the baseline, dropping the oldest", () => {
    const { ids, issued } = createIds();
    let draft = newGuestDraft(exam(), ids);
    const storedStepIds: string[] = [];

    for (let index = 1; index <= 11; index += 1) {
      const outcome = store(draft, exam(`Steg ${index}`), ids);
      draft = outcome.draft;
      storedStepIds.push(outcome.step.history.position_step_id);
    }

    expect(draft.steps).toHaveLength(10);
    expect(draft.baseline.step_id).toBe(DOCUMENT_ID);
    expect(draft.steps.map((step) => step.step_id)).toEqual(storedStepIds.slice(1));
    expect(draft.steps.map((step) => step.document.title)).toEqual(
      Array.from({ length: 10 }, (_, index) => `Steg ${index + 2}`),
    );
    expect(draft.position_step_id).toBe(draft.steps[9]?.step_id);
    expect(draft.cursor).toBe(draft.position_step_id);
    expect(guestHistory(draft).step_ids).toEqual(draft.steps.map((step) => step.step_id));

    for (const step of draft.steps) {
      expect(issued).toContain(step.step_id);
    }
  });

  it("drops every redo step when a new step branches after an earlier snapshot", () => {
    const { ids } = createIds();
    let draft = newGuestDraft(exam(), ids);
    const first = store(draft, exam("A"), ids);
    draft = first.draft;
    const firstStepId = first.step.history.position_step_id;
    const second = store(draft, exam("B"), ids);
    draft = second.draft;
    const third = store(draft, exam("C"), ids);
    draft = third.draft;

    const branched = store(draft, exam("D"), ids, firstStepId);

    expect(branched.draft.steps.map((step) => step.document.title)).toEqual(["A", "D"]);
    expect(branched.draft.steps.map((step) => step.step_id)).toEqual([
      firstStepId,
      branched.draft.position_step_id,
    ]);
    expect(branched.draft.cursor).toBe(branched.draft.position_step_id);

    const fromBaseline = store(branched.draft, exam("E"), ids, branched.draft.baseline.step_id);

    expect(fromBaseline.draft.steps.map((step) => step.document.title)).toEqual(["E"]);
    expect(fromBaseline.draft.position_step_id).toBe(fromBaseline.draft.steps[0]?.step_id);
  });

  it("refuses a stale cursor without changing the draft or consuming an id", () => {
    const { ids, issued } = createIds();
    const draft = newGuestDraft(exam(), ids);
    const before = structuredClone(draft);
    const issuedBefore = issued.length;

    const outcome = storeGuestUndoStep(
      draft,
      {
        afterStepId: null,
        document: exam("Senare"),
        expectedCursor: "99999999-9999-4999-8999-999999999999",
      },
      ids,
    );

    expect(outcome).toEqual({ kind: "conflict" });
    expect(draft).toEqual(before);
    expect(issued).toHaveLength(issuedBefore);
  });

  it("refuses a document the save rules reject without changing the draft", () => {
    const { ids, issued } = createIds();
    const draft = newGuestDraft(exam(), ids);
    const before = structuredClone(draft);
    const issuedBefore = issued.length;
    const refused = refusedExam();
    const copy = examWorkspaceSaveRefusalCopy(refused.items);
    expect(copy).not.toBeNull();

    const outcome = storeGuestUndoStep(
      draft,
      { afterStepId: null, document: refused, expectedCursor: draft.cursor },
      ids,
    );

    expect(outcome).toEqual({ kind: "refused", copy });
    expect(draft).toEqual(before);
    expect(issued).toHaveLength(issuedBefore);
  });

  it("refuses Spara with a stale revision without changing the draft", () => {
    const { ids } = createIds();
    const draft = newGuestDraft(exam(), ids);
    const before = structuredClone(draft);

    const outcome = saveGuestDraft(
      draft,
      {
        document: exam("Ny"),
        expectedRevision: draft.saved_document.revision + 1,
        positionStepId: draft.position_step_id,
      },
      ids,
    );

    expect(outcome).toEqual({ kind: "conflict" });
    expect(draft).toEqual(before);
  });

  it("increments the saved revision once and rotates the cursor on Spara", () => {
    const { ids, issued } = createIds();
    let draft = newGuestDraft(exam(), ids);
    const stored = store(draft, titled(exam(), "Redigerad"), ids);
    draft = stored.draft;
    const stepId = stored.step.history.position_step_id;
    const cursorBefore = draft.cursor;
    const issuedBefore = issued.length;

    const outcome = saveGuestDraft(
      draft,
      {
        document: titled(exam(), "Redigerad"),
        expectedRevision: 1,
        positionStepId: stepId,
      },
      ids,
    );

    expect(outcome.kind).toBe("ok");
    if (outcome.kind !== "ok") {
      return;
    }
    expect(outcome.draft.saved_document.revision).toBe(2);
    expect(outcome.draft.saved_document.title).toBe("Redigerad");
    expect(outcome.draft.cursor).not.toBe(cursorBefore);
    expect(issued.slice(issuedBefore)).toContain(outcome.draft.cursor);
    expect(outcome.draft.position_step_id).toBe(stepId);
    expect(outcome.draft.steps.map((step) => step.step_id)).toEqual([stepId]);
    expect(outcome.response.document.revision).toBe(2);
    expect(outcome.response.saved_document.revision).toBe(2);
    expect(outcome.response.summary.version).toBe(2);
    expect(outcome.response.summary.vault_file_id).toBe(outcome.draft.lineage_id);
    expect(outcome.response.history_cursor).toBe(outcome.draft.cursor);
    expect(outcome.response.document.title).toBe("Redigerad");
  });

  it("appends the saved copy after the position when no snapshot holds it", () => {
    const { ids } = createIds();
    let draft = newGuestDraft(exam(), ids);
    const first = store(draft, exam("A"), ids);
    draft = first.draft;
    const firstStepId = first.step.history.position_step_id;
    const second = store(draft, exam("B"), ids);
    draft = second.draft;

    const outcome = saveGuestDraft(
      draft,
      {
        document: exam("Sparad"),
        expectedRevision: 1,
        positionStepId: firstStepId,
      },
      ids,
    );

    expect(outcome.kind).toBe("ok");
    if (outcome.kind !== "ok") {
      return;
    }
    expect(outcome.draft.steps.map((step) => step.document.title)).toEqual(["A", "Sparad"]);
    expect(outcome.draft.position_step_id).toBe(outcome.draft.steps[1]?.step_id);
    expect(outcome.draft.saved_document.revision).toBe(2);
    expect(outcome.draft.steps[1]?.document.revision).toBe(2);
  });

  it("returns a read step's document without moving the stored position", () => {
    const { ids } = createIds();
    let draft = newGuestDraft(exam(), ids);
    const first = store(draft, exam("A"), ids);
    draft = first.draft;
    const firstStepId = first.step.history.position_step_id;
    const second = store(draft, exam("B"), ids);
    draft = second.draft;
    const secondStepId = second.step.history.position_step_id;

    const read = guestHistoryStep(draft, firstStepId);

    expect(read.kind).toBe("ok");
    if (read.kind !== "ok") {
      return;
    }
    expect(read.step.step_id).toBe(firstStepId);
    expect(read.step.document.title).toBe("A");
    // Reading a step never moves the stored position; only a write does.
    expect(draft.position_step_id).toBe(secondStepId);
    expect(guestDocumentResponse(draft).document.title).toBe("B");
  });

  it("opens the newest branched step after a write follows an earlier snapshot", () => {
    const { ids } = createIds();
    let draft = newGuestDraft(exam(), ids);
    const first = store(draft, exam("A"), ids);
    draft = first.draft;
    const firstStepId = first.step.history.position_step_id;
    const second = store(draft, exam("B"), ids);
    draft = second.draft;

    // The editor stood on the earlier snapshot; its next write branches there and drops B.
    const branched = store(draft, exam("C"), ids, firstStepId);
    draft = branched.draft;

    const opened = guestDocumentResponse(draft);

    expect(opened.document.title).toBe("C");
    expect(opened.document.revision).toBe(1);
    expect(opened.saved_document.title).toBe("Original");
    expect(opened.summary.version).toBe(1);
    expect(opened.summary.lineage_id).toBe(DOCUMENT_ID);
    expect(opened.history_cursor).toBe(draft.cursor);
    expect(opened.notes).toEqual([]);
    expect(opened.conversion).toBeNull();
    expect(opened.export_blockers).toEqual([]);
    expect(draft.steps.map((step) => step.document.title)).toEqual(["A", "C"]);
  });

  it("reports an unknown history step as not found", () => {
    const { ids } = createIds();
    const draft = newGuestDraft(exam(), ids);

    expect(guestHistoryStep(draft, "99999999-9999-4999-8999-999999999999")).toEqual({
      kind: "not_found",
    });
  });
});
