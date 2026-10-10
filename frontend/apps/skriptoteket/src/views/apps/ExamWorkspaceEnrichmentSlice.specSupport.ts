/**
 * Exam workspace answer-key proposal slice test harness.
 *
 * Slice purpose:
 *   Lock the advisory answer-key loop: request proposals for the saved head
 *   revision, poll until the job settles, show each proposal next to its
 *   item, and let the teacher approve, adjust, or dismiss it.
 *
 * Relationships:
 *   - Shared fixtures and interactions for the enrichment specs (polling,
 *     drawer, review, rejection).
 *   - Builds on `ExamWorkspaceSlice.specSupport.ts` for the document fixture
 *     and view mounting.
 *   - Each spec owns its own `api/examWorkspace` module mock and passes it in.
 */

import { flushPromises } from "@vue/test-utils";
import type { Mock } from "vitest";

import type {
  ExamWorkspaceDocumentResponse,
  ExamWorkspaceEnrichmentStatus,
  NativeExamItem,
} from "../../api/examWorkspace";
import { buildResponse, type ViewWrapper } from "./ExamWorkspaceSlice.specSupport";

/** The `api/examWorkspace` module mock every enrichment spec declares. */
export interface EnrichmentApiMocks {
  downloadExamWorkspaceExport: Mock;
  getExamWorkspaceDocument: Mock;
  getExamWorkspaceEnrichment: Mock;
  importExamWorkspaceDocument: Mock;
  getExamWorkspaceConversionStatus: Mock;
  listExamWorkspaceDocuments: Mock;
  saveExamWorkspaceDocument: Mock;
  startExamWorkspaceEnrichment: Mock;
}

/** Item 2 arrives without a key, so it is the one the provider proposes for. */
export function buildUnkeyedResponse(version: number): ExamWorkspaceDocumentResponse {
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

export function status(
  state: ExamWorkspaceEnrichmentStatus["state"],
  extra: Partial<ExamWorkspaceEnrichmentStatus> = {},
): ExamWorkspaceEnrichmentStatus {
  return { document_revision: 1, lineage_id: "lineage-1", proposals: [], state, ...extra };
}

export const SUCCEEDED = status("succeeded", {
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

/** Resets every API mock and imports an unkeyed document with no job requested. */
export function resetEnrichmentApiMocks(apiMocks: EnrichmentApiMocks): void {
  for (const mock of Object.values(apiMocks)) {
    mock.mockReset();
  }
  apiMocks.getExamWorkspaceConversionStatus.mockResolvedValue({
    job_id: "job-1", lineage_id: "lineage-1", state: "succeeded", error_message: null,
  });
  apiMocks.importExamWorkspaceDocument.mockImplementation(async () => {
    apiMocks.getExamWorkspaceDocument.mockResolvedValueOnce(buildUnkeyedResponse(1));
    return { job_id: "job-1", lineage_id: "lineage-1", state: "queued", error_message: null };
  });
  apiMocks.listExamWorkspaceDocuments.mockResolvedValue({ documents: [] });
  apiMocks.getExamWorkspaceEnrichment.mockResolvedValue(status("not_requested"));
}

export function lastSavedItem(saveMock: Mock, itemId: string): NativeExamItem | undefined {
  const calls = saveMock.mock.calls;
  const [, params] = calls[calls.length - 1] as [
    string,
    { document: { items: NativeExamItem[] } },
  ];
  return params.document.items.find((item) => item.item_id === itemId);
}

export async function requestProposals(wrapper: ViewWrapper) {
  await wrapper.find('[data-test="exam-workspace-enrichment-request"]').trigger("click");
  await flushPromises();
}
