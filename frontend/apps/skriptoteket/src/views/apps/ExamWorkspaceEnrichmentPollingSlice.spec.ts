/**
 * Exam workspace answer-key suggestion request and polling behavior.
 *
 * Slice purpose:
 *   Lock the request half of the AI suggestion loop: request suggestions
 *   for the questions exactly as the editor shows them, poll until the job
 *   settles, and write each arriving suggestion onto its question.
 *
 * Expected behavior:
 *   Requests work while the editor has unsaved changes, an arriving
 *   suggestion for a keyless question becomes its key as
 *   `machine_proposed`, a failed poll retries with a doubling delay and
 *   toasts once per failure streak, and polling stops when the job settles
 *   or the view unmounts.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../stores/toast";
import type { NativeExamDocument, NativeExamItem } from "../../api/examWorkspace";
import { EXAM_WORKSPACE_ENRICHMENT_POLL_MS } from "./exam-workspace/useExamWorkspaceEnrichment";
import {
  requestProposals,
  resetEnrichmentApiMocks,
  status,
  SUCCEEDED,
} from "./ExamWorkspaceEnrichmentSlice.specSupport";
import {
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
  selectItemRow,
} from "./ExamWorkspaceSlice.specSupport";


const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
}));
const exportApiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => exportApiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const STATUS_FAILURE_COPY = "Det gick inte att hämta facitförslagen. Försök igen.";

/** The newest stored step's version of one question. */
function lastStoredItem(storeMock: { mock: { calls: unknown[][] } }, itemId: string) {
  const calls = storeMock.mock.calls;
  const [, request] = calls[calls.length - 1] as [string, { document: NativeExamDocument }];
  return request.document.items.find((item: NativeExamItem) => item.item_id === itemId);
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((pendingResolve) => {
    resolve = pendingResolve;
  });
  return { promise, resolve };
}

function statusFailureToastCount(): number {
  return vi
    .mocked(useToastStore().failure)
    .mock.calls.filter(([message]) => message === STATUS_FAILURE_COPY).length;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  resetEnrichmentApiMocks(apiMocks);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ExamWorkspaceView answer-key suggestion request and polling", () => {
  it("polls a queued job until it succeeds and writes the suggestion onto its question", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceAnswerKeySuggestions
      .mockResolvedValueOnce(status("running"))
      .mockResolvedValueOnce(SUCCEEDED);

    await requestProposals(wrapper);
    expect(apiMocks.requestExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
    const [lineageId, sentDocument, itemId] =
      apiMocks.requestExamWorkspaceAnswerKeySuggestions.mock.calls[0];
    expect(lineageId).toBe("lineage-1");
    expect(itemId).toBeUndefined();
    expect(
      sentDocument.items.find((item: { item_id: string }) => item.item_id === "item_002")
        ?.answer_key.origin,
    ).toBe("absent");
    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "Facitförslagen väntar på tur.",
    );

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toContain(
      "tas fram",
    );

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();
    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "1 facitförslag har lagts in på frågorna.",
    );
    // The suggestion was written onto the question, so storing it is pending.
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 3);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(2);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledWith(
      "lineage-1",
      "job-suggest-1",
    );

    await saveDocument(wrapper);
    const saved = lastStoredItem(apiMocks.storeExamWorkspaceUndoStep, "item_002");
    expect(saved?.answer_key.origin).toBe("machine_proposed");
    expect(saved?.answer_key.correct_choice_ids).toEqual(["choice_003"]);
    expect(saved?.ai_suggestion?.correct_choice_ids).toEqual(["choice_003"]);
    expect(saved?.review.state).toBe("review_required");
  });

  it("applies suggestions a failed job produced before its provider failure", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(
      status("failed", {
        message: "Facitförslaget kunde inte hämtas just nu. Försök igen senare.",
        suggestions: SUCCEEDED.suggestions,
      }),
    );

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "Facitförslaget kunde inte hämtas just nu. Försök igen senare.",
    );
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toBe("Sparar …");
    await saveDocument(wrapper);
    const saved = lastStoredItem(apiMocks.storeExamWorkspaceUndoStep, "item_002");
    expect(saved?.ai_suggestion?.correct_choice_ids).toEqual(["choice_003"]);
  });

  it("shows the server message when no suggestions can be made", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(
      status("not_eligible", { message: "Inga facitförslag kan skapas." }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await requestProposals(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "Inga facitförslag kan skapas.",
    );
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(0);
  });

  it("can be requested while the editor has unsaved changes", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_001");
    await wrapper.find('[data-test="exam-workspace-item-points-input"]').setValue("7");

    expect(
      wrapper.find('[data-test="exam-workspace-suggest-all"]').attributes("disabled"),
    ).toBeUndefined();

    await requestProposals(wrapper);
    const [, sentDocument] = apiMocks.requestExamWorkspaceAnswerKeySuggestions.mock.calls[0];
    expect(
      sentDocument.items.find(
        (item: { item_id: string; points: number | null }) => item.item_id === "item_001",
      )?.points,
    ).toBe(7);
  });

  it("retries a failed poll on the next interval until the job settles", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceAnswerKeySuggestions
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(SUCCEEDED);

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();
    expect(
      wrapper.find('[data-test="exam-workspace-suggest-all"]').attributes("disabled"),
    ).toBeDefined();

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "1 facitförslag har lagts in på frågorna.",
    );
    expect(
      wrapper.find('[data-test="exam-workspace-suggest-all"]').attributes("disabled"),
    ).toBeUndefined();
  });

  it("shows one failure toast per failed-poll streak and keeps polling with backoff", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceAnswerKeySuggestions.mockRejectedValue(new Error("network"));

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 2);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 4);
    await flushPromises();

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(3);
    expect(statusFailureToastCount()).toBe(1);
    expect(
      wrapper.find('[data-test="exam-workspace-suggest-all"]').attributes("disabled"),
    ).toBeDefined();

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 8);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(4);
    expect(statusFailureToastCount()).toBe(1);
  });

  it("shows the failure toast again after a successful poll ends the streak", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceAnswerKeySuggestions
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(status("running"))
      .mockRejectedValueOnce(new Error("network"));

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(3);
    expect(statusFailureToastCount()).toBe(2);
  });

  it("does not start polling when the view unmounts while the request is in flight", async () => {
    const pendingRequest = deferred<ReturnType<typeof status>>();
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockReturnValue(pendingRequest.promise);
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await requestProposals(wrapper);
    wrapper.unmount();
    pendingRequest.resolve(status("queued"));
    await flushPromises();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 3);

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(0);
  });

  it("does not schedule another poll when the view unmounts while a poll is in flight", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    const pendingPoll = deferred<ReturnType<typeof status>>();
    apiMocks.getExamWorkspaceAnswerKeySuggestions.mockReturnValueOnce(pendingPoll.promise);

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
    wrapper.unmount();
    pendingPoll.resolve(status("running"));
    await flushPromises();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 3);

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
  });

  it("stops polling when the view unmounts", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(status("running"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await requestProposals(wrapper);
    const callsBeforeUnmount = apiMocks.getExamWorkspaceAnswerKeySuggestions.mock.calls.length;

    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 3);

    expect(apiMocks.getExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(callsBeforeUnmount);
  });
});
