/**
 * Exam workspace export blocker panel: one AI key request for every missing key.
 *
 * Slice purpose:
 *   With two or more questions blocked by "facit saknas", the panel offers
 *   "Föreslå facit för alla (N)": one suggestions request for the whole exam,
 *   after which every row waits for its own Godkänn (no approve-all).
 */

import { DOMWrapper, flushPromises } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NativeExamItem } from "../../api/examWorkspace";
import {
  SUCCEEDED_CONVERSION,
  SUGGESTION,
  resetEnrichmentApiMocks,
  status,
} from "./ExamWorkspaceEnrichmentSlice.specSupport";
import { buildResponse, importFixtureDocument, mountExamWorkspace, type ViewWrapper } from "./ExamWorkspaceSlice.specSupport";

const apiMocks = vi.hoisted(() => ({
  downloadExamWorkspaceExport: vi.fn(),
  findExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceAnswerKeySuggestions: vi.fn(),
  getExamWorkspaceDocument: vi.fn(),
  importExamWorkspaceDocument: vi.fn(),
  getExamWorkspaceConversionStatus: vi.fn(),
  listExamWorkspaceDocuments: vi.fn(),
  requestExamWorkspaceAnswerKeySuggestions: vi.fn(),
  saveExamWorkspaceDocument: vi.fn(),
}));

vi.mock("../../api/examWorkspaceExports", () => apiMocks);
vi.mock("../../api/examWorkspace", async () => ({
  ...apiMocks,
  getExamCourseCatalog: (await import("../../test/examCourseCatalog")).getExamCourseCatalog,
}));

const UNKEYED = ["item_002", "item_003", "item_004"];

function unkeyed(item: NativeExamItem): NativeExamItem {
  return {
    ...item,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    gaps: item.gaps.map((gap) => ({ ...gap, accepted_values: [] })),
    review: { ...item.review, state: "review_complete" },
  };
}

const wrappers: ViewWrapper[] = [];

beforeEach(() => {
  resetEnrichmentApiMocks(apiMocks);
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    const response = buildResponse({ conversion: SUCCEEDED_CONVERSION, version: 1 });
    for (const document of [response.document, response.saved_document]) {
      document.items = document.items.map((item) => (UNKEYED.includes(item.item_id) ? unkeyed(item) : item));
    }
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(response);
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
      document_revision: null, questions_total: 0, questions_done: 0, units: [] };
  });
});

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount();
  document.body.replaceChildren();
});

function page(testId: string): DOMWrapper<HTMLElement> | null {
  const element = document.body.querySelector<HTMLElement>(`[data-test="${testId}"]`);
  return element ? new DOMWrapper(element) : null;
}

async function openMenu(wrapper: ViewWrapper): Promise<void> {
  await wrapper.get('[data-test="exam-workspace-export"]').trigger("click");
  await flushPromises();
}

describe("ExamWorkspaceView export blocker panel, Föreslå facit för alla", () => {
  it("asks for every missing key in one request and turns each row into its own Godkänn", async () => {
    apiMocks.requestExamWorkspaceAnswerKeySuggestions.mockResolvedValue(
      status("succeeded", {
        suggestions: [
          { item_id: "item_002", suggestion: SUGGESTION },
          { item_id: "item_003", suggestion: { ...SUGGESTION, correct_choice_ids: ["choice_001", "choice_002"] } },
          {
            item_id: "item_004",
            suggestion: { ...SUGGESTION, correct_choice_ids: [], gap_accepted_values: [{ accepted_values: ["100"], gap_id: "gap_001" }] },
          },
        ],
      }),
    );
    const { wrapper } = await mountExamWorkspace({}, "desktop", document.body);
    wrappers.push(wrapper);
    await importFixtureDocument(wrapper);

    await openMenu(wrapper);
    for (const itemId of UNKEYED) {
      expect(page(`exam-workspace-blocker-${itemId}`)!.text()).toBe(`Fråga ${itemId.slice(-1)}: facit saknas`);
    }
    expect(page("exam-workspace-blocker-suggest-all")!.text()).toBe("Föreslå facit för alla (3)");
    await page("exam-workspace-blocker-suggest-all")!.trigger("click");
    await flushPromises();

    expect(apiMocks.requestExamWorkspaceAnswerKeySuggestions).toHaveBeenCalledTimes(1);
    expect(apiMocks.requestExamWorkspaceAnswerKeySuggestions.mock.calls[0]![2]).toBeUndefined();
    for (const itemId of UNKEYED) {
      expect(page(`exam-workspace-blocker-${itemId}`)!.text()).toBe(`Fråga ${itemId.slice(-1)}: facit ej granskat`);
      expect(page(`exam-workspace-blocker-fix-${itemId}`)!.text()).toBe("Godkänn");
    }
    // Every key still waits for its own review: no button approves them all.
    expect(page("exam-workspace-blocker-suggest-all")).toBeNull();
    expect(document.body.textContent).not.toContain("Godkänn alla");
    expect(page("exam-workspace-export-qti")!.attributes("aria-disabled")).toBe("true");
  });

  it("offers no batch button for a single missing key; the row keeps its own Föreslå facit", async () => {
    apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
      const response = buildResponse({ conversion: SUCCEEDED_CONVERSION, version: 1 });
      for (const document of [response.document, response.saved_document]) {
        document.items = document.items.map((item) =>
          item.item_id === "item_002" ? unkeyed(item) : UNKEYED.includes(item.item_id) ? { ...item, answer_key: { ...item.answer_key, origin: "teacher_authored" } } : item,
        );
      }
      apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(response);
      return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null, summary: null,
        document_revision: null, questions_total: 0, questions_done: 0, units: [] };
    });
    const { wrapper } = await mountExamWorkspace({}, "desktop", document.body);
    wrappers.push(wrapper);
    await importFixtureDocument(wrapper);

    await openMenu(wrapper);

    expect(page("exam-workspace-blocker-suggest-all")).toBeNull();
    expect(page("exam-workspace-blocker-fix-item_002")!.text()).toBe("Föreslå facit");
  });
});
