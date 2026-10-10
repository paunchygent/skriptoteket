/**
 * Exam workspace answer-key proposal rejection on save.
 *
 * Slice purpose:
 *   Lock which proposals a workspace save reports as rejected, so the server
 *   carries every other pending proposal forward to the new revision.
 *
 * Expected behavior:
 *   Only the explicit dismiss action rejects a proposal. Approving it or
 *   moving it into the editor with Redigera förslaget hides it without
 *   rejecting it. Rejected ids are sent with the next save and cleared after
 *   it succeeds; a network or conflict failure keeps them for the retry.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../../api/client";
import {
  buildUnkeyedResponse,
  lastSavedItem,
  resetEnrichmentApiMocks,
  SUCCEEDED,
} from "./ExamWorkspaceEnrichmentSlice.specSupport";
import {
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

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  resetEnrichmentApiMocks(apiMocks);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ExamWorkspaceView answer-key proposal rejection on save", () => {
  it("does not reject a proposal moved into the editor with Redigera förslaget", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await selectItemRow(wrapper, "item_002");
    await wrapper.get('[data-test="exam-workspace-proposal-edit"]').trigger("click");

    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenLastCalledWith(
      "lineage-1",
      expect.objectContaining({ rejectedProposalItemIds: [] }),
    );
    expect(lastSavedItem(apiMocks.saveExamWorkspaceDocument, "item_002")?.answer_key.origin).toBe(
      "machine_proposed",
    );
    wrapper.unmount();
  });

  it("does not reject an approved proposal", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await selectItemRow(wrapper, "item_002");
    await wrapper.get('[data-test="exam-workspace-proposal-approve"]').trigger("click");

    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenLastCalledWith(
      "lineage-1",
      expect.objectContaining({ rejectedProposalItemIds: [] }),
    );
    wrapper.unmount();
  });

  it("sends rejected proposal ids and clears them after a successful save", async () => {
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
    apiMocks.saveExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await selectItemRow(wrapper, "item_002");
    await wrapper.get('[data-test="exam-workspace-proposal-dismiss"]').trigger("click");
    await wrapper.get('[data-test="exam-workspace-item-title-input"]').setValue("Ändrad titel");

    await saveDocument(wrapper);

    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenLastCalledWith(
      "lineage-1",
      expect.objectContaining({ rejectedProposalItemIds: ["item_002"] }),
    );
    await wrapper.get('[data-test="exam-workspace-item-title-input"]').setValue("Nästa titel");
    await saveDocument(wrapper);
    expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenLastCalledWith(
      "lineage-1",
      expect.objectContaining({ rejectedProposalItemIds: [] }),
    );
    wrapper.unmount();
  });

  it.each(["network", "conflict"])(
    "retains rejected proposal ids after a %s save failure for the retry",
    async (failure) => {
      apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);
      apiMocks.saveExamWorkspaceDocument.mockRejectedValueOnce(
        failure === "conflict"
          ? new ApiError({ code: "CONFLICT", status: 409, message: "conflict" })
          : new Error("network"),
      );
      apiMocks.getExamWorkspaceDocument.mockResolvedValue(buildUnkeyedResponse(2));
      const { wrapper } = await mountExamWorkspace();
      await importFixtureDocument(wrapper);
      await selectItemRow(wrapper, "item_002");
      await wrapper.get('[data-test="exam-workspace-proposal-dismiss"]').trigger("click");
      await wrapper.get('[data-test="exam-workspace-item-title-input"]').setValue("Ändrad titel");

      await saveDocument(wrapper);

      expect(wrapper.find('[data-test="exam-workspace-proposal-panel"]').exists()).toBe(false);
      await wrapper.get('[data-test="exam-workspace-item-title-input"]').setValue("Försök igen");
      apiMocks.saveExamWorkspaceDocument.mockResolvedValueOnce(buildUnkeyedResponse(3));
      await saveDocument(wrapper);
      expect(apiMocks.saveExamWorkspaceDocument).toHaveBeenLastCalledWith(
        "lineage-1",
        expect.objectContaining({ rejectedProposalItemIds: ["item_002"] }),
      );
      wrapper.unmount();
    },
  );
});
