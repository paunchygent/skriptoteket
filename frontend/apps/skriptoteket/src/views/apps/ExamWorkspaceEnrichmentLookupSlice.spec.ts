/**
 * Exam workspace: a failed lookup of a lost suggestion job (TASK-SKRIPT-39-04-09 P1, repair 1 F2).
 *
 * Slice purpose:
 *   Lock the wiring for a failed lost-job lookup: the notice under the header
 *   shows the failure with a retry button, and clicking it asks the server
 *   again for the open exam's saved version.
 *
 * Expected behavior:
 *   The failure shows in the notice under the header; `Försök igen`
 *   reruns the lookup; a job found then is delivered and the failure line
 *   and button disappear.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  resetEnrichmentApiMocks,
  SUCCEEDED,
} from "./ExamWorkspaceEnrichmentSlice.specSupport";
import { importFixtureDocument, mountExamWorkspace } from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceHistory: vi.fn(),
  getExamWorkspaceHistoryStep: vi.fn(),
  moveExamWorkspaceHistoryPosition: vi.fn(),
  storeExamWorkspaceUndoStep: vi.fn(),
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

const LOOKUP_ERROR = '[data-test="exam-workspace-enrichment-lookup-error"]';
const LOOKUP_RETRY = '[data-test="exam-workspace-enrichment-lookup-retry"]';

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  resetEnrichmentApiMocks(apiMocks);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("ExamWorkspaceView failed lost-job lookup", () => {
  it("shows the failure in the header notice and reruns the lookup from its retry button", async () => {
    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockRejectedValueOnce(new Error("network"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);

    expect(wrapper.find(LOOKUP_ERROR).text()).toBe(
      "Kunde inte hämta väntande facitförslag.",
    );
    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);

    apiMocks.findExamWorkspaceAnswerKeySuggestions.mockResolvedValueOnce(SUCCEEDED);
    await wrapper.find(LOOKUP_RETRY).trigger("click");
    await flushPromises();

    expect(apiMocks.findExamWorkspaceAnswerKeySuggestions.mock.calls).toEqual([
      ["lineage-1", 1],
      ["lineage-1", 1],
    ]);
    expect(wrapper.find('[data-test="exam-workspace-enrichment-message"]').text()).toBe(
      "1 facitförslag har lagts in på frågorna.",
    );
    expect(wrapper.get('[data-test="exam-workspace-save-state"]').text()).toContain("Sparar …");
    expect(wrapper.find(LOOKUP_ERROR).exists()).toBe(false);
    expect(wrapper.find(LOOKUP_RETRY).exists()).toBe(false);
  });
});
