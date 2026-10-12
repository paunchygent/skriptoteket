/**
 * Progressive DOCX conversion at the real workspace view boundary (D30): the
 * first saved batch opens for editing while later batches arrive. A
 * placeholder cannot be changed until its batch is merged into the open copy,
 * each later batch replaces its own placeholders, and the teacher's edits of
 * converted items survive every later revision and a conflicting save.
 */
import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import type {
  ExamWorkspaceConversionStatus,
  ExamWorkspaceConversionUnit,
  ExamWorkspaceDocumentResponse,
  NativeExamItem,
} from "../../api/examWorkspace";
import { EXAM_WORKSPACE_CONFLICT_COPY, EXAM_WORKSPACE_CONVERSION_POLL_MS } from "./exam-workspace/useExamWorkspaceDocument";
import {
  buildFreeTextItem,
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  selectItemRow,
  type ViewWrapper,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceEnrichment: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  startExamWorkspaceEnrichment: vi.fn(),
}));
vi.mock("../../api/examWorkspace", () => apiMocks);

type UnitState = ExamWorkspaceConversionUnit["state"];

function placeholder(sequence: number): NativeExamItem {
  return {
    ...buildFreeTextItem(sequence),
    body: [{ segments: [{ kind: "text", text: `Källtext ${sequence}` }] }],
    review: {
      confidence: 0,
      parse_origin: "llm_parsed",
      reasons: ["Frågan konverteras fortfarande."],
      state: "review_required",
    },
  };
}

function converted(sequence: number): NativeExamItem {
  return { ...buildFreeTextItem(sequence), title: `Konverterad ${sequence}` };
}

function revision(version: number, items: NativeExamItem[]): ExamWorkspaceDocumentResponse {
  const response = buildResponse({ version });
  return { ...response, document: { ...response.document, items } };
}

function status(
  state: ExamWorkspaceConversionStatus["state"],
  documentRevision: number | null,
  units: UnitState[],
): ExamWorkspaceConversionStatus {
  return {
    job_id: "job-1",
    lineage_id: "lineage-1",
    state,
    error_message: null,
    document_revision: documentRevision,
    questions_total: 3,
    questions_done: units.filter((unit) => unit !== "converting").length,
    units: units.map((unitState, index) => ({
      unit_id: `q${index + 1}`,
      question: true,
      state: unitState,
      item_ids: [`item_00${index + 1}`],
    })),
  };
}

const FIRST = revision(1, [converted(1), placeholder(2), placeholder(3)]);
const FIRST_STATUS = status("running", 1, ["ready", "converting", "converting"]);
const SECOND = revision(2, [converted(1), converted(2), converted(3)]);
const SECOND_STATUS = status("running", 2, ["ready", "ready", "ready"]);

let wrapper: ViewWrapper | undefined;

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  for (const mock of Object.values(apiMocks)) mock.mockReset();
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(status("queued", null, []));
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(FIRST_STATUS);
  apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(FIRST);
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.getExamWorkspaceEnrichment.mockResolvedValue({
    lineage_id: "lineage-1", document_revision: 1, state: "not_requested", proposals: [],
  });
});
afterEach(() => {
  wrapper?.unmount();
  wrapper = undefined;
  vi.useRealTimers();
});

async function uploadFirstBatch(): Promise<ViewWrapper> {
  const mounted = await mountExamWorkspace();
  wrapper = mounted.wrapper;
  await importFixtureDocument(wrapper);
  return wrapper;
}

async function tick() {
  await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_CONVERSION_POLL_MS);
  await flushPromises();
}

async function editTitle(view: ViewWrapper, itemId: string, title: string) {
  await selectItemRow(view, itemId);
  await view.get('[data-test="exam-workspace-item-title-input"]').setValue(title);
}

async function titleOf(view: ViewWrapper, itemId: string): Promise<string> {
  await selectItemRow(view, itemId);
  return (view.get('[data-test="exam-workspace-item-title-input"]').element as HTMLInputElement).value;
}

/** Dispatch an input event straight on the element, past its `disabled` attribute. */
async function forceInput(view: ViewWrapper, control: string, value: string) {
  const element = view.get(`[data-test="${control}"]`).element as HTMLInputElement;
  element.value = value;
  element.dispatchEvent(new Event("input"));
  await flushPromises();
}

const EDIT_CONTROLS = [
  "exam-workspace-item-title-input",
  "exam-workspace-item-points-input",
  "exam-workspace-marking-guide-input",
];

/** Every edit control of the selected item's editor is enabled, or every one is disabled. */
function expectEditable(view: ViewWrapper, editable: boolean) {
  for (const control of EDIT_CONTROLS) {
    expect(view.get(`[data-test="${control}"]`).attributes("disabled"), control).toBe(editable ? undefined : "");
  }
  const body = view.get('[data-test="exam-workspace-body-paragraph-0"]').attributes("contenteditable");
  if (editable) {
    expect(body).not.toBe("false");
  } else {
    expect(body).toBe("false");
  }
  const markReviewed = view.find('[data-test="exam-workspace-mark-reviewed"]');
  if (markReviewed.exists()) {
    expect(markReviewed.attributes("disabled")).toBe(editable ? undefined : "");
  }
}

function convertingNoticeShown(view: ViewWrapper): boolean {
  return view.find('[data-test="exam-workspace-converting-notice"]').exists();
}

describe("Exam workspace progressive conversion", () => {
  it("opens the first batch for editing, marks converting questions and fills them as batches arrive", async () => {
    const view = await uploadFirstBatch();

    expect(view.get('[data-test="exam-workspace-conversion-status"]').text()).toContain(
      "Konverterar provet: 1 av 3 frågor klara.",
    );
    expect(view.get('[data-test="exam-workspace-summary-title"]').text()).toBe("NO-prov HT25");
    await selectItemRow(view, "item_001");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    await selectItemRow(view, "item_002");
    expect(convertingNoticeShown(view)).toBe(true);
    expect(view.text()).toContain("Källtext 2");
    expect(view.find('[data-test="exam-workspace-mark-reviewed"]').exists()).toBe(true);
    expectEditable(view, false);

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(view.get('[data-test="exam-workspace-conversion-status"]').text()).toContain("3 av 3 frågor klara.");
    expect(convertingNoticeShown(view)).toBe(false);
    expectEditable(view, true);
    expect(await titleOf(view, "item_002")).toBe("Konverterad 2");

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded", 2, ["ready", "ready", "ready"]));
    await tick();
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(apiMocks.importExamWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("refuses every change to a converting placeholder, even one dispatched past its disabled controls", async () => {
    const view = await uploadFirstBatch();
    await selectItemRow(view, "item_002");
    await forceInput(view, "exam-workspace-item-title-input", "Lärarens rubrik två");
    await forceInput(view, "exam-workspace-item-points-input", "7");
    await forceInput(view, "exam-workspace-marking-guide-input", "Lärarens bedömningsstöd");

    expect(view.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
    expect(view.get('[data-test="exam-workspace-save"]').attributes("disabled")).toBe("");
    await selectItemRow(view, "item_001");
    await selectItemRow(view, "item_002");
    expect((view.get('[data-test="exam-workspace-item-title-input"]').element as HTMLInputElement).value).toBe("Fråga 2");
    expect((view.get('[data-test="exam-workspace-item-points-input"]').element as HTMLInputElement).value).toBe("2");
  });

  it("keeps unsaved edits of converted items and fills a placeholder from its batch when it arrives", async () => {
    const view = await uploadFirstBatch();
    await editTitle(view, "item_001", "Lärarens rubrik ett");
    await selectItemRow(view, "item_003");
    await forceInput(view, "exam-workspace-item-title-input", "Lärarens rubrik tre");
    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");
    expect(await titleOf(view, "item_003")).toBe("Fråga 3");

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await tick();

    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");
    expect(await titleOf(view, "item_002")).toBe("Konverterad 2");
    expect(await titleOf(view, "item_003")).toBe("Konverterad 3");
    expectEditable(view, true);

    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(revision(3, SECOND.document.items));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    const [, params] = apiMocks.saveExamWorkspaceDocument.mock.calls[0];
    expect(params.expectedRevision).toBe(2);
    expect(params.document.items.map((item: NativeExamItem) => item.title)).toEqual([
      "Lärarens rubrik ett",
      "Konverterad 2",
      "Konverterad 3",
    ]);
  });

  it("keeps a placeholder locked until the final revision that arrived during a save is merged", async () => {
    const view = await uploadFirstBatch();
    await editTitle(view, "item_001", "Lärarens rubrik ett");
    let resolveSave!: (value: ExamWorkspaceDocumentResponse) => void;
    apiMocks.saveExamWorkspaceDocument.mockReturnValueOnce(new Promise((resolve) => { resolveSave = resolve; }));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");

    const savedFirst = revision(2, [{ ...converted(1), title: "Lärarens rubrik ett" }, placeholder(2), placeholder(3)]);
    const finalItems = [{ ...converted(1), title: "Lärarens rubrik ett" }, converted(2), converted(3)];
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("succeeded", 3, ["ready", "ready", "ready"]));
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(revision(3, finalItems));
    await tick();
    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);

    resolveSave(savedFirst);
    await flushPromises();
    // The status already reports every batch ready, but its revision is not merged yet.
    await selectItemRow(view, "item_002");
    expect(convertingNoticeShown(view)).toBe(true);
    expectEditable(view, false);
    await tick();

    expect(convertingNoticeShown(view)).toBe(false);

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(apiMocks.getExamWorkspaceConversionStatus).toHaveBeenCalledTimes(2);
    expect(await titleOf(view, "item_002")).toBe("Konverterad 2");
    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");
    expect(view.find('[data-test="exam-workspace-conversion-status"]').exists()).toBe(false);
  });

  it("saves again on the newer revision when conversion saved one during the teacher's save", async () => {
    const view = await uploadFirstBatch();
    await editTitle(view, "item_001", "Lärarens rubrik ett");

    apiMocks.saveExamWorkspaceDocument
      .mockRejectedValueOnce(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }))
      .mockResolvedValueOnce(revision(3, SECOND.document.items));
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(SECOND);
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    const [, retry] = apiMocks.saveExamWorkspaceDocument.mock.calls[1];
    expect(retry.expectedRevision).toBe(2);
    expect(retry.document.items.map((item: NativeExamItem) => item.title)).toEqual([
      "Lärarens rubrik ett",
      "Konverterad 2",
      "Konverterad 3",
    ]);
    expect(view.text()).not.toContain(EXAM_WORKSPACE_CONFLICT_COPY);
  });

  it("merges and saves the teacher's edits when a save conflicts while a status poll is still in flight", async () => {
    const view = await uploadFirstBatch();
    await editTitle(view, "item_001", "Lärarens rubrik ett");

    let resolvePoll!: (value: ExamWorkspaceConversionStatus) => void;
    apiMocks.getExamWorkspaceConversionStatus
      .mockReturnValueOnce(new Promise((resolve) => { resolvePoll = resolve; }))
      .mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(SECOND);
    apiMocks.saveExamWorkspaceDocument
      .mockRejectedValueOnce(new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }))
      .mockResolvedValueOnce(revision(3, SECOND.document.items));
    await tick();
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    resolvePoll(SECOND_STATUS);
    await flushPromises();

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    const [, retry] = apiMocks.saveExamWorkspaceDocument.mock.calls[1];
    expect(retry.expectedRevision).toBe(2);
    expect(retry.document.items.map((item: NativeExamItem) => item.title)).toEqual([
      "Lärarens rubrik ett",
      "Konverterad 2",
      "Konverterad 3",
    ]);
    expect(view.text()).not.toContain(EXAM_WORKSPACE_CONFLICT_COPY);
  });

  it("keeps the teacher's copy and merges it later when another batch moves the head past the conflict's status", async () => {
    const view = await uploadFirstBatch();
    await editTitle(view, "item_001", "Lärarens rubrik ett");

    // The save from revision 1 conflicts; the status then describes revision 2,
    // but another batch commits revision 3 before the document is read.
    const third = revision(3, [converted(1), converted(2), converted(3)]);
    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(SECOND_STATUS);
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(third);
    apiMocks.saveExamWorkspaceDocument.mockRejectedValueOnce(
      new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }),
    );
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(view.text()).not.toContain(EXAM_WORKSPACE_CONFLICT_COPY);
    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");

    apiMocks.getExamWorkspaceConversionStatus.mockResolvedValueOnce(status("running", 3, ["ready", "ready", "ready"]));
    await tick();
    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");
    expect(await titleOf(view, "item_002")).toBe("Konverterad 2");

    apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(revision(4, third.document.items));
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();
    const [, retry] = apiMocks.saveExamWorkspaceDocument.mock.calls[1];
    expect(retry.expectedRevision).toBe(3);
    expect(retry.document.items.map((item: NativeExamItem) => item.title)).toEqual([
      "Lärarens rubrik ett",
      "Konverterad 2",
      "Konverterad 3",
    ]);
  });

  it("keeps the teacher's copy when the conflicting revision cannot be fetched", async () => {
    const view = await uploadFirstBatch();
    await editTitle(view, "item_001", "Lärarens rubrik ett");

    apiMocks.getExamWorkspaceConversionStatus.mockRejectedValueOnce(new Error("offline"));
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(SECOND);
    apiMocks.saveExamWorkspaceDocument.mockRejectedValueOnce(
      new ApiError({ code: "CONFLICT", message: "Konflikt", status: 409 }),
    );
    await view.get('[data-test="exam-workspace-save"]').trigger("click");
    await flushPromises();

    expect(apiMocks.getExamWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(await titleOf(view, "item_001")).toBe("Lärarens rubrik ett");
  });
});
