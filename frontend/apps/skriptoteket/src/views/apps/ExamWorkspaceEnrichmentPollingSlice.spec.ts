/**
 * Exam workspace answer-key proposal request and polling behavior.
 *
 * Slice purpose:
 *   Lock the request half of the advisory answer-key loop: request proposals
 *   for the saved head revision, poll until the job settles, and show each
 *   proposal next to its item.
 *
 * Expected behavior:
 *   Proposals never change the document on arrival.
 *   Requests need a saved document, a failed poll retries with a doubling
 *   delay and toasts once per failure streak, and polling stops when the job settles or the view unmounts.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useToastStore } from "../../stores/toast";
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
  selectItemRow,
} from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceEnrichment: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
  startExamWorkspaceEnrichment: vi.fn(),
}));

vi.mock("../../api/examWorkspace", () => apiMocks);

const STATUS_FAILURE_COPY = "Det gick inte att hämta facitförslagen. Försök igen.";

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

describe("ExamWorkspaceView answer-key proposal request and polling", () => {
  it("polls a queued job until it succeeds and shows the proposal without changing the document", async () => {
    apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceEnrichment.mockReset();
    apiMocks.getExamWorkspaceEnrichment
      .mockResolvedValueOnce(status("running"))
      .mockResolvedValueOnce(SUCCEEDED);

    await requestProposals(wrapper);
    expect(apiMocks.startExamWorkspaceEnrichment).toHaveBeenCalledWith("lineage-1");
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
      "1 facitförslag att granska.",
    );
    expect(wrapper.find('[data-test="exam-workspace-item-proposal-item_002"]').exists()).toBe(
      true,
    );
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 3);
    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(2);

    await selectItemRow(wrapper, "item_002");
    expect(wrapper.find('[data-test="exam-workspace-proposal-choices"]').text()).toContain(
      "Nederbörd",
    );
  });

  it("shows the server message when no proposals can be made", async () => {
    apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(
      status("not_eligible", { message: "Inga facitförslag kan skapas." }),
    );
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await requestProposals(wrapper);

    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "Inga facitförslag kan skapas.",
    );
    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(1);
  });

  it("needs a saved document before proposals can be requested", async () => {
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_001");
    await wrapper.find('[data-test="exam-workspace-item-title-input"]').setValue("Ändrad");

    expect(
      wrapper.find('[data-test="exam-workspace-enrichment-request"]').attributes("disabled"),
    ).toBeDefined();
  });

  it("retries a failed poll on the next interval until the job settles", async () => {
    apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceEnrichment.mockReset();
    apiMocks.getExamWorkspaceEnrichment
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(SUCCEEDED);

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();
    expect(
      wrapper.find('[data-test="exam-workspace-enrichment-request"]').attributes("disabled"),
    ).toBeDefined();

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();

    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(2);
    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "1 facitförslag att granska.",
    );
    expect(wrapper.find('[data-test="exam-workspace-item-proposal-item_002"]').exists()).toBe(
      true,
    );
    expect(
      wrapper.find('[data-test="exam-workspace-enrichment-request"]').attributes("disabled"),
    ).toBeUndefined();
  });

  it("shows one failure toast per failed-poll streak and keeps polling with backoff", async () => {
    apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceEnrichment.mockReset();
    apiMocks.getExamWorkspaceEnrichment.mockRejectedValue(new Error("network"));

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 2);
    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 4);
    await flushPromises();

    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(3);
    expect(statusFailureToastCount()).toBe(1);
    expect(
      wrapper.find('[data-test="exam-workspace-enrichment-request"]').attributes("disabled"),
    ).toBeDefined();

    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 8);
    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(4);
    expect(statusFailureToastCount()).toBe(1);
  });

  it("shows the failure toast again after a successful poll ends the streak", async () => {
    apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    apiMocks.getExamWorkspaceEnrichment.mockReset();
    apiMocks.getExamWorkspaceEnrichment
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(status("running"))
      .mockRejectedValueOnce(new Error("network"));

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();

    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(3);
    expect(statusFailureToastCount()).toBe(2);
  });

  it("stops polling when the view unmounts", async () => {
    apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(status("running"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await requestProposals(wrapper);
    const callsBeforeUnmount = apiMocks.getExamWorkspaceEnrichment.mock.calls.length;

    wrapper.unmount();
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS * 3);

    expect(apiMocks.getExamWorkspaceEnrichment).toHaveBeenCalledTimes(callsBeforeUnmount);
  });
});
