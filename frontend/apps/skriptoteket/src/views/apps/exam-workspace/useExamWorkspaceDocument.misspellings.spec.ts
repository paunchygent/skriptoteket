/**
 * Teacher-keyed gap misspellings through the document state.
 *
 * Expected behavior:
 *   Adding accepted answers keys them at once and asks the producer for the
 *   misspellings of exactly the added values, with the question's gold answers
 *   and the document's text. A reply merges into the gap as it stands then:
 *   existing automatic values stay, and a duplicate, a gold answer and a
 *   spelling the teacher suppressed are dropped. A reply that lost its place
 *   stays silent: a newer key edit of the gap, a removed keyed value, another
 *   opening, a reloaded copy or a reconverted question all drop it. A reply
 *   merged while a save is in flight is re-applied when the save installs a
 *   copy the payload was read without, and a failed request that still stands
 *   reports Swedish copy.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceMisspellingsRequest,
  ExamWorkspaceMisspellingsResponse,
  NativeExamDocument,
  NativeExamGap,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { gapItem } from "./examWorkspaceKeyedItems.specSupport";
import {
  buildResponse,
  currentDocument,
  currentItem,
  deferred,
  openMatchingDocument as openWith,
  savedResponse,
} from "./useExamWorkspaceDocument.specSupport";
import type { DocumentState } from "./useExamWorkspaceDocument.specSupport";

const AUTOMATIC_VALUES_FAILURE_COPY =
  "Det gick inte att skapa automatiska stavningar. Svaren finns kvar.";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceDocument: vi.fn(),
  requestExamWorkspaceAnswerMisspellings: vi.fn(),
  retryExamWorkspaceItem: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

function keyedGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ...gapItem(
      "teacher_authored",
      [
        ["gap_001", ["Stockholm"]],
        ["gap_002", ["Oslo"]],
      ],
      null,
    ),
    ...overrides,
  };
}

function retryableGapItem(): NativeExamItem {
  return keyedGapItem({
    retry_source: {
      chunks: [
        {
          anchor: "body:0001",
          images: [],
          missing_images: [],
          kind: "question",
          marked_text: "Hon heter [___] och [___].",
          paragraphs: [],
          runs: [],
          text: "Hon heter [___] och [___].",
        },
      ],
      context_chunks: [],
      owned_context_anchors: [],
      key_chunks: [],
      label_kind: "gap_fill",
    },
  });
}

async function openKeyedDocument(item: NativeExamItem = keyedGapItem()): Promise<DocumentState> {
  return await openWith(apiMocks.getExamWorkspaceDocument, item);
}

function gapOf(state: DocumentState, gapId = "gap_001"): NativeExamGap {
  const gap = currentItem(state).gaps.find((candidate) => candidate.gap_id === gapId);
  if (!gap) {
    throw new Error("expected a loaded gap");
  }
  return gap;
}

function lastMisspellingsRequest(): ExamWorkspaceMisspellingsRequest {
  const calls = apiMocks.requestExamWorkspaceAnswerMisspellings.mock.calls;
  return calls[calls.length - 1]![0] as ExamWorkspaceMisspellingsRequest;
}

function pendingReply() {
  return deferred<ExamWorkspaceMisspellingsResponse>();
}

beforeEach(() => {
  setActivePinia(createPinia());
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.requestExamWorkspaceAnswerMisspellings.mockResolvedValue({ automatic_values: [] });
});

describe("keyed gap misspellings in useExamWorkspaceDocument", () => {
  it("keys a new answer at once, asks only for the added value, and merges the reply", async () => {
    const pending = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockReturnValue(pending.promise);
    const state = await openKeyedDocument();

    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);

    expect(gapOf(state).accepted_values).toEqual(["Stockholm", "Göteborg"]);
    const request = lastMisspellingsRequest();
    expect(request.accepted_values).toEqual(["Göteborg"]);
    expect(request.other_gold_answers).toEqual(["Stockholm", "Göteborg", "Oslo"]);
    expect(request.document_text).toContain("English 1");
    expect(request.document_text).toContain("Hon heter");

    pending.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual(["Götebprg"]);
  });

  it("keeps existing automatic values and drops a reply's duplicates, gold answers and case variants", async () => {
    const item = keyedGapItem();
    item.gaps[0]!.automatic_values = ["Stockhom"];
    const state = await openKeyedDocument(item);
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockResolvedValue({
      automatic_values: ["götebprg", "Stockholm", "stockhom", "götebprg", "Götebörg"],
    });

    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual(["Stockhom", "götebprg", "Götebörg"]);
  });

  it("never re-adds a removed spelling through a later key edit or reply", async () => {
    const item = keyedGapItem();
    item.gaps[0]!.automatic_values = ["Stockhom", "Stokholm"];
    const state = await openKeyedDocument(item);

    state.removeItemAutomaticValue("item_001", "gap_001", "Stokholm");

    expect(gapOf(state).automatic_values).toEqual(["Stockhom"]);
    expect(gapOf(state).excluded_automatic_values).toEqual(["Stokholm"]);

    apiMocks.requestExamWorkspaceAnswerMisspellings.mockResolvedValue({
      automatic_values: ["Stokholm"],
    });
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    await flushPromises();
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg", "Malmö"]);
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual(["Stockhom"]);
  });

  it("saves the suppression and keeps it when the saved document is reopened", async () => {
    const item = keyedGapItem();
    item.gaps[0]!.automatic_values = ["Stockhom"];
    const state = await openKeyedDocument(item);
    state.removeItemAutomaticValue("item_001", "gap_001", "Stockhom");
    const copy = currentDocument(state);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(savedResponse({ ...copy, revision: 2 }));

    expect(await state.saveDocument("position-1")).toBe(true);

    const payload = apiMocks.saveExamWorkspaceDocument.mock.calls[0]![1]
      .document as NativeExamDocument;
    expect(payload.items[0]!.gaps[0]!.excluded_automatic_values).toEqual(["Stockhom"]);

    apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse(payload.items[0]!));
    expect(await state.openDocument("lineage-1")).toBe(true);
    expect(gapOf(state).excluded_automatic_values).toEqual(["Stockhom"]);
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockResolvedValue({
      automatic_values: ["Stockhom"],
    });
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual([]);
  });

  it("carries still-pending accepted values into a newer key edit", async () => {
    const first = pendingReply();
    const second = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const state = await openKeyedDocument();

    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg", "Malmö"]);

    first.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();
    expect(gapOf(state).automatic_values).toEqual([]);

    expect(lastMisspellingsRequest().accepted_values).toEqual(["Göteborg", "Malmö"]);
    second.resolve({ automatic_values: ["Götebprg", "Malmöe"] });
    await flushPromises();
    expect(gapOf(state).automatic_values).toEqual(["Götebprg", "Malmöe"]);
  });

  it("regenerates only the retained pending values after a partial removal", async () => {
    const first = pendingReply();
    const second = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    const state = await openKeyedDocument();
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg", "Malmö"]);
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    expect(lastMisspellingsRequest().accepted_values).toEqual(["Göteborg"]);
    first.resolve({ automatic_values: ["Götebprg", "Malmöe"] });
    await flushPromises();
    expect(gapOf(state).automatic_values).toEqual([]);
    second.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();
    expect(gapOf(state).automatic_values).toEqual(["Götebprg"]);
  });

  it("drops a reply whose keyed value was removed before it arrived", async () => {
    const pending = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockReturnValue(pending.promise);
    const state = await openKeyedDocument();

    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm"]);
    pending.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual([]);
  });

  it("drops a reply when the same lineage was reloaded with the same keyed values", async () => {
    const pending = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockReturnValue(pending.promise);
    const state = await openKeyedDocument();
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);

    apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildResponse(keyedGapItem()));
    await state.reloadDocument();
    pending.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual([]);
  });

  it("drops a reply when another exam was opened meanwhile", async () => {
    const pending = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockReturnValue(pending.promise);
    const state = await openKeyedDocument();
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);

    const other = buildResponse(keyedGapItem());
    apiMocks.getExamWorkspaceDocument.mockResolvedValue({
      ...other,
      summary: { ...other.summary, lineage_id: "lineage-2" },
    });
    expect(await state.openDocument("lineage-2")).toBe(true);
    pending.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual([]);
  });

  it("drops a reply when a retry replaced the question with the same keyed values", async () => {
    const pending = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockReturnValue(pending.promise);
    const state = await openKeyedDocument(retryableGapItem());
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);

    apiMocks.retryExamWorkspaceItem.mockResolvedValue({
      item: keyedGapItem(),
      lineage_id: "lineage-1",
    });
    await state.retryItem("item_001", "gap_fill");
    pending.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();

    expect(gapOf(state).automatic_values).toEqual([]);
  });

  it("re-applies a reply merged during a save when the response replaces the copy", async () => {
    const pending = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockReturnValue(pending.promise);
    const state = await openKeyedDocument();
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);

    const savePending = deferred<ExamWorkspaceDocumentResponse>();
    apiMocks.saveExamWorkspaceDocument.mockReturnValue(savePending.promise);
    const saving = state.saveDocument("position-1");

    pending.resolve({ automatic_values: ["Götebprg"] });
    await flushPromises();
    expect(gapOf(state).automatic_values).toEqual(["Götebprg"]);

    const payload = apiMocks.saveExamWorkspaceDocument.mock.calls[0]![1]
      .document as NativeExamDocument;
    savePending.resolve(savedResponse(payload));
    await saving;

    expect(gapOf(state).automatic_values).toEqual(["Götebprg"]);
    expect(state.isDirty.value).toBe(true);
  });

  it("reports a failed request that still stands and keeps the keyed edit", async () => {
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockRejectedValue(new Error("boom"));
    const state = await openKeyedDocument();

    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    await flushPromises();

    expect(
      useToastStore().toasts.some(
        (toast) => toast.variant === "failure" && toast.message === AUTOMATIC_VALUES_FAILURE_COPY,
      ),
    ).toBe(true);
    expect(gapOf(state).accepted_values).toEqual(["Stockholm", "Göteborg"]);
  });

  it("stays silent when a failed request already lost its place", async () => {
    const pending = pendingReply();
    apiMocks.requestExamWorkspaceAnswerMisspellings.mockReturnValue(pending.promise);
    const state = await openKeyedDocument();

    state.updateItemGapValues("item_001", "gap_001", ["Stockholm", "Göteborg"]);
    state.updateItemGapValues("item_001", "gap_001", ["Stockholm"]);
    pending.reject(new Error("boom"));
    await flushPromises();

    expect(useToastStore().toasts).toEqual([]);
  });
});
