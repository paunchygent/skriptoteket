/**
 * Exam workspace answer-key proposal drawer behavior.
 *
 * Slice purpose:
 *   Lock how an arriving proposal is surfaced next to its item in each
 *   workspace layout.
 *
 * Expected behavior:
 *   On desktop a waiting proposal opens the proposal drawer. On tablet and
 *   phone the drawer stays closed and focus stays where the teacher left it;
 *   the item details toggle shows a badge instead.
 */

import { flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
  getExamWorkspaceConversionStatus: vi.fn(),
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

describe("ExamWorkspaceView answer-key proposal drawer", () => {
  it("opens the desktop drawer for a waiting proposal", async () => {
    apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(status("queued"));
    const { wrapper } = await mountExamWorkspace();
    await importFixtureDocument(wrapper);
    await selectItemRow(wrapper, "item_002");
    apiMocks.getExamWorkspaceEnrichment.mockReset();
    apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);

    await requestProposals(wrapper);
    await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
    await flushPromises();

    expect(wrapper.find('[data-test="exam-workspace-proposal-panel"]').exists()).toBe(true);
  });

  it.each(["tablet", "phone"] as const)(
    "keeps the %s drawer closed and focus in place when a proposal arrives",
    async (layout) => {
      apiMocks.startExamWorkspaceEnrichment.mockResolvedValue(status("queued"));
      const { wrapper } = await mountExamWorkspace({}, layout, document.body);
      await importFixtureDocument(wrapper);
      if (layout === "tablet") {
        await selectItemRow(wrapper, "item_002");
      } else {
        await wrapper.get('[data-test="exam-workspace-phone-next"]').trigger("click");
      }
      await wrapper.get('[data-test="exam-workspace-mode-filer"]').trigger("click");
      await requestProposals(wrapper);
      await wrapper.get('[data-test="exam-workspace-mode-redigera"]').trigger("click");
      const title = wrapper.get('[data-test="exam-workspace-item-title-input"]')
        .element as HTMLInputElement;
      title.focus();
      apiMocks.getExamWorkspaceEnrichment.mockReset();
      apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(SUCCEEDED);

      await vi.advanceTimersByTimeAsync(EXAM_WORKSPACE_ENRICHMENT_POLL_MS);
      await flushPromises();

      expect(wrapper.find('[data-test="exam-workspace-item-drawer"]').exists()).toBe(false);
      expect(document.activeElement).toBe(title);
      const badge = wrapper.get('[data-test="exam-workspace-item-details-toggle"] span');
      expect(Number(badge.text())).toBeGreaterThan(0);
      wrapper.unmount();
    },
  );
});
