/**
 * AI suggestion jobs belong to the opening of the exam that requested them
 * (TASK-SKRIPT-39-04-07, repair 4 case space E).
 *
 * Expected behavior:
 *   A job's results, status, failure toast and next poll take effect only
 *   while the exam opening that requested it is still open. The check runs
 *   at the moment each completion lands, so a completion that settles in the
 *   same turn as the open of another exam never reaches that exam. Reopening
 *   the first exam later is a new opening, so the old job stays ended.
 *
 * Rows follow case space E in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-07/repair4/design.md`.
 */

import { flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import type {
  ExamWorkspaceAnswerKeySuggestionsStatus,
  ExamWorkspaceDocumentResponse,
  NativeAnswerKeySuggestion,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { useToastStore } from "../../../stores/toast";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";
import { buildResponse, currentItem, deferred } from "./useExamWorkspaceDocument.specSupport";
import { useExamWorkspaceDocument } from "./useExamWorkspaceDocument";
import {
  EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS,
  EXAM_WORKSPACE_ENRICHMENT_POLL_MS,
  useExamWorkspaceEnrichment,
} from "./useExamWorkspaceEnrichment";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const STATUS_FAILURE_COPY = "Det gick inte att hämta facitförslagen. Försök igen.";
const REQUEST_FAILURE_COPY = "Det gick inte att begära facitförslag. Försök igen.";

const SUGGESTION: NativeAnswerKeySuggestion = {
  correct_choice_ids: [],
  fingerprint: "a".repeat(64),
  gap_accepted_values: [],
  match_pairs: [
    { left_id: "left_001", right_id: "right_001" },
    { left_id: "left_002", right_id: "right_002" },
    { left_id: "left_003", right_id: "right_003" },
  ],
  model: "model",
  prompt_template_version: "v1",
  provider_profile_id: "profile",
};

/** Both exams reuse the converter's ids, so a misdelivered suggestion fits. */
function keylessItem(): NativeExamItem {
  return buildMatchingItem({
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
  });
}

function examResponse(lineageId: string): ExamWorkspaceDocumentResponse {
  const base = buildResponse(keylessItem());
  const document = { ...base.document, document_id: lineageId };
  return {
    ...base,
    document,
    saved_document: document,
    summary: { ...base.summary, lineage_id: lineageId },
  };
}

function jobStatus(
  state: ExamWorkspaceAnswerKeySuggestionsStatus["state"],
  withSuggestion = false,
): ExamWorkspaceAnswerKeySuggestionsStatus {
  return {
    job_id: "job-a",
    lineage_id: "lineage-a",
    state,
    suggestions: withSuggestion ? [{ item_id: "item_001", suggestion: SUGGESTION }] : [],
  };
}

function toastCount(message: string): number {
  return useToastStore().toasts.filter((toast) => toast.message === message).length;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  setActivePinia(createPinia());
  for (const mock of [...Object.values(apiMocks), ...Object.values(exportApiMocks)]) {
    mock.mockReset();
  }
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
});

async function openExamA() {
  apiMocks.getExamWorkspaceDocument.mockResolvedValue(examResponse("lineage-a"));
  const scope = effectScope();
  const composed = scope.run(() => {
    const document = useExamWorkspaceDocument();
    const enrichment = useExamWorkspaceEnrichment({
      applySuggestions: document.applyArrivingSuggestions,
      document: document.workspaceDocument,
      isOpen: document.isOpen,
      openExam: document.openExam,
      savedRevision: document.savedRevision,
    });
    return { document, enrichment };
  });
  if (!composed) {
    throw new Error("expected the composed workspace state");
  }
  await composed.document.openDocument("lineage-a");
  return composed;
}

/** Exam A has a queued job whose status poll is in flight. */
async function examAWithPollInFlight() {
  const composed = await openExamA();
  apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(jobStatus("queued"));
  const poll = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
  apiMocks.getExamWorkspaceAnswerKeySuggestions.mockReturnValue(poll.promise);
  await composed.enrichment.requestSuggestionsForAll();
  await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
  expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
  return { ...composed, poll };
}

/** Start opening exam B and hold its response. */
function startOpeningB(state: ReturnType<typeof useExamWorkspaceDocument>) {
  const response = deferred<ExamWorkspaceDocumentResponse>();
  apiMocks.getExamWorkspaceDocument.mockReturnValue(response.promise);
  const opening = state.openDocument("lineage-b");
  return { opening, response };
}

function expectExamBUntouched(state: ReturnType<typeof useExamWorkspaceDocument>): void {
  expect(state.summary.value?.lineage_id).toBe("lineage-b");
  expect(currentItem(state).ai_suggestion ?? null).toBeNull();
  expect(currentItem(state).answer_key.origin).toBe("absent");
  expect(state.isDirty.value).toBe(false);
}

async function expectNoFurtherPoll(calls: number): Promise<void> {
  await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_MAX_POLL_MS * 2);
  expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(calls);
}

describe("a completion settling in the same turn as the open of another exam", () => {
  it("E2: a succeeded poll writes nothing into the newly opened exam", async () => {
    const { document, enrichment, poll } = await examAWithPollInFlight();
    const { opening, response } = startOpeningB(document);

    response.resolve(examResponse("lineage-b"));
    poll.resolve(jobStatus("succeeded", true));
    await opening;
    await flushPromises();

    expectExamBUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("E3: a succeeded request response writes nothing into the newly opened exam", async () => {
    const { document, enrichment } = await openExamA();
    const request = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValue(request.promise);
    const requesting = enrichment.requestSuggestionsForAll();
    const { opening, response } = startOpeningB(document);

    response.resolve(examResponse("lineage-b"));
    request.resolve(jobStatus("succeeded", true));
    await opening;
    await requesting;
    await flushPromises();

    expectExamBUntouched(document);
    expect(enrichment.enrichmentStatus.value).toBeNull();
  });

  it("E4: a running poll shows no status and schedules no next poll", async () => {
    const { document, enrichment, poll } = await examAWithPollInFlight();
    const { opening, response } = startOpeningB(document);

    response.resolve(examResponse("lineage-b"));
    poll.resolve(jobStatus("running"));
    await opening;
    await flushPromises();

    expect(enrichment.enrichmentStatus.value).toBeNull();
    expect(enrichment.isEnrichmentPending.value).toBe(false);
    await expectNoFurtherPoll(1);
  });

  it("E5: a failed poll shows no toast and schedules no retry", async () => {
    const { document, poll } = await examAWithPollInFlight();
    const { opening, response } = startOpeningB(document);

    response.resolve(examResponse("lineage-b"));
    poll.reject(new Error("network down"));
    await opening;
    await flushPromises();

    expect(toastCount(STATUS_FAILURE_COPY)).toBe(0);
    await expectNoFurtherPoll(1);
  });

  it("E5: a failed request shows no toast on the newly opened exam", async () => {
    const { document, enrichment } = await openExamA();
    const request = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValue(request.promise);
    const requesting = enrichment.requestSuggestionsForAll();
    const { opening, response } = startOpeningB(document);

    response.resolve(examResponse("lineage-b"));
    request.reject(new Error("network down"));
    await opening;
    await requesting;
    await flushPromises();

    expect(toastCount(REQUEST_FAILURE_COPY)).toBe(0);
  });
});

describe("a job of an exam that is no longer open", () => {
  it("E8: reopening exam A later does not revive A's old poll", async () => {
    const { document, enrichment, poll } = await examAWithPollInFlight();
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(examResponse("lineage-b"));
    await document.openDocument("lineage-b");
    await flushPromises();
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(examResponse("lineage-a"));
    await document.openDocument("lineage-a");
    await flushPromises();

    poll.resolve(jobStatus("succeeded", true));
    await flushPromises();

    expect(currentItem(document).ai_suggestion ?? null).toBeNull();
    expect(currentItem(document).answer_key.origin).toBe("absent");
    expect(enrichment.enrichmentStatus.value).toBeNull();
    await expectNoFurtherPoll(1);
  });

  it("E10: exam B can request while A's request is still in flight, and A's return leaves B's job alone", async () => {
    const { document, enrichment } = await openExamA();
    const requestA = deferred<ExamWorkspaceAnswerKeySuggestionsStatus>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(requestA.promise);
    const requestingA = enrichment.requestSuggestionsForAll();
    apiMocks.getExamWorkspaceDocument.mockResolvedValue(examResponse("lineage-b"));
    await document.openDocument("lineage-b");
    await flushPromises();

    const statusB: ExamWorkspaceAnswerKeySuggestionsStatus = {
      ...jobStatus("queued"),
      job_id: "job-b",
      lineage_id: "lineage-b",
    };
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(statusB);
    await enrichment.requestSuggestionsForAll();
    expect(apiMocks.requestExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(2);
    expect(enrichment.enrichmentStatus.value).toEqual(statusB);

    requestA.resolve(jobStatus("succeeded", true));
    await requestingA;
    await flushPromises();

    expectExamBUntouched(document);
    expect(enrichment.enrichmentStatus.value).toEqual(statusB);
    expect(enrichment.isEnrichmentPending.value).toBe(true);
  });
});

describe("a job of the exam that stays open", () => {
  it("E14: keeps delivering after a manual reload of the same exam", async () => {
    const { document, enrichment, poll } = await examAWithPollInFlight();
    await document.reloadDocument();
    await flushPromises();

    poll.resolve(jobStatus("succeeded", true));
    await flushPromises();

    expect(currentItem(document).ai_suggestion).toEqual(SUGGESTION);
    expect(currentItem(document).answer_key.origin).toBe("machine_proposed");
    expect(enrichment.enrichmentStatus.value?.state).toBe("succeeded");
  });
});
