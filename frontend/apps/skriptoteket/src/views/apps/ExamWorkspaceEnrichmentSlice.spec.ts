/**
 * Exam workspace answer-key proposal slice behavior.
 *
 * Slice purpose:
 *   Lock the advisory answer-key loop: request proposals for the saved head
 *   revision, poll until the job settles, show each proposal next to its
 *   item, and let the teacher approve, adjust, or dismiss it.
 *
 * Expected behavior:
 *   Proposals never change the document on arrival. Approving unchanged
 *   saves the key as `reviewed_advisory` and leaves the item's review state
 *   as it was; adjusting it in the editor saves it as `teacher_authored`.
 *   Requests need a saved document, a failed poll retries on the next
 *   interval, and polling stops when the job settles or the view unmounts.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEnrichmentStatus,
  NativeExamItem,
} from "../../api/examWorkspace";
import { EXAM_WORKSPACE_ENRICHMENT_POLL_MS } from "./exam-workspace/useExamWorkspaceEnrichment";
import {
  buildResponse,
  importFixtureDocument,
  mountExamWorkspace,
  saveDocument,
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

/** Item 2 arrives without a key, so it is the one the provider proposes for. */
function buildUnkeyedResponse(version: number): ExamWorkspaceDocumentResponse {
  const response = buildResponse({ version });
  return {
    ...response,
    document: {
      ...response.document,
      items: response.document.items.map((item) =>
        item.item_id === "item_002"
          ? {
              ...item,
              answer_key: { correct_choice_ids: [], origin: "absent" },
              review: { ...item.review, reasons: ["facit saknas"], state: "review_required" },
            }
          : item,
      ),
    },
  };
}

function proposedItem(): NativeExamItem {
  const item = buildUnkeyedResponse(1).document.items.find(
    (candidate) => candidate.item_id === "item_002",
  );
  if (!item) {
    throw new Error("fixture item_002 missing");
  }
  return {
    ...item,
    answer_key: { correct_choice_ids: ["choice_c"], origin: "machine_proposed" },
    review: {
      ...item.review,
      reasons: [...item.review.reasons, "machine_proposed_answer_key"],
      state: "review_required",
    },
  };
}

function status(
  state: ExamWorkspaceEnrichmentStatus["state"],
  extra: Partial<ExamWorkspaceEnrichmentStatus> = {},
): ExamWorkspaceEnrichmentStatus {
  return { document_revision: 1, lineage_id: "lineage-1", proposals: [], state, ...extra };
}

const SUCCEEDED = status("succeeded", {
  proposals: [
    {
      item_id: "item_002",
      model: "luna-low",
      prompt_template_version: "v1",
      proposed_item: proposedItem(),
      provider_profile_id: "luna",
    },
  ],
});

function lastSavedItem(itemId: string): NativeExamItem | undefined {
  const calls = apiMocks.saveExamWorkspaceDocument.mock.calls;
  const [, params] = calls[calls.length - 1] as [
    string,
    { document: { items: NativeExamItem[] } },
  ];
  return params.document.items.find((item) => item.item_id === itemId);
}

async function requestProposals(wrapper: Awaited<ReturnType<typeof mountExamWorkspace>>["wrapper"]) {
  await wrapper.find('[data-test="exam-workspace-enrichment-request"]').trigger("click");
  await flushPromises();
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.importExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(1));
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(status("not_requested"));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ExamWorkspaceView answer-key proposal slice", () => {
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

  it("saves an unchanged approved proposal as reviewed_advisory without completing review", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-approve"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-proposal-panel"]').exists()).toBe(false);
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_002"]').text(),
    ).toContain("Behöver granskas");

    await saveDocument(wrapper);

    const saved = lastSavedItem("item_002");
    expect(saved?.answer_key).toEqual({
      correct_choice_ids: ["choice_c"],
      origin: "reviewed_advisory",
    });
    expect(saved?.review).toEqual({
      confidence: 0.9,
      parse_origin: "deterministic",
      reasons: ["facit saknas"],
      state: "review_required",
    });
  });

  it("keeps parse-confidence review required after approving a proposal", async () => {
    const parseReviewResponse = buildUnkeyedResponse(1);
    parseReviewResponse.document.items = parseReviewResponse.document.items.map((item) =>
      item.item_id === "item_002"
        ? {
            ...item,
            review: {
              ...item.review,
              reasons: ["sublines_without_answer_keys"],
              state: "review_required",
            },
          }
        : item,
    );
    apiMocks.importExamWorkspaceDocument.mockResolvedValue(parseReviewResponse);
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-approve"]').trigger("click");
    await saveDocument(wrapper);

    const saved = lastSavedItem("item_002");
    expect(saved?.answer_key.origin).toBe("reviewed_advisory");
    expect(saved?.review.state).toBe("review_required");
    expect(saved?.review.reasons).toEqual(["sublines_without_answer_keys"]);
  });

  it("saves an adjusted proposal as teacher_authored", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-edit"]').trigger("click");
    expect(
      wrapper
        .find<HTMLInputElement>('[data-test="exam-workspace-choice-correct-choice_c"]')
        .element.checked,
    ).toBe(true);
    expect(
      wrapper.find('[data-test="exam-workspace-item-status-item_002"]').text(),
    ).toContain("Behöver granskas");

    await wrapper.find('[data-test="exam-workspace-choice-correct-choice_a"]').setValue(true);
    await wrapper.find('[data-test="exam-workspace-mark-reviewed"]').trigger("click");
    await saveDocument(wrapper);

    const saved = lastSavedItem("item_002");
    expect(saved?.answer_key).toEqual({
      correct_choice_ids: ["choice_a"],
      origin: "teacher_authored",
    });
    expect(saved?.review.state).toBe("review_complete");
  });

  it("keeps a dismissed proposal out of the document", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    await selectItemRow(wrapper, "item_002");
    await wrapper.find('[data-test="exam-workspace-proposal-dismiss"]').trigger("click");

    expect(wrapper.find('[data-test="exam-workspace-proposal-panel"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="exam-workspace-dirty-pill"]').exists()).toBe(false);
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
